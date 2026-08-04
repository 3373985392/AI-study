---
title: "从 CLI Chat 到浏览器 Web Chat：邀请码门禁与流式接口实践"
date: 2026-08-04
tags: [AI Agent, Web Chat, FastAPI, SSE, SQLite, 安全, 项目实战]
categories: [项目实战]
description: "把命令行聊天助手拆成可复用服务，增加 FastAPI 流式接口、邀请码认证、额度控制和 VitePress 浏览器界面"
author: ZhuanZ
---

今天完成了 `cli-chat` 从命令行程序到浏览器 Web Chat 的第一版改造。这个过程最重要的变化不是“多了一个输入框”，而是重新划分了客户端、服务端和访问控制的边界。

最终的访问链路是：

```text
浏览器
  └─ chienzz.top/chat
       ├─ 邀请码门禁
       ├─ 本地保存聊天历史
       └─ /api/chat/stream
            └─ Nginx 反向代理
                 └─ FastAPI
                      ├─ 会话与额度校验
                      ├─ ChatService
                      └─ OpenAI 兼容模型 / RAG
```

API Key、邀请码摘要、会话令牌和额度数据都留在服务器，浏览器只负责展示界面和发送当前会话需要的上下文。

## 一、为什么 CLI 程序不能直接挂到域名下

最初的 `cli-chat/chat.py` 负责四件事情：

1. 从终端读取用户输入。
2. 在一个全局列表中保存聊天历史。
3. 调用普通聊天模型或 RAG 模型。
4. 把流式结果打印到终端。

它适合一个人在 SSH 会话中使用，却不适合 Web 服务。尤其是全局 `messages` 列表，如果多个浏览器用户共用同一个 Python 进程，就可能出现会话串线：用户 A 的问题被带进用户 B 的上下文。

因此第一步不是写前端，而是把模型调用从终端循环中抽出来：

```text
终端 / Web API
       ↓
无状态 ChatService
       ↓
普通聊天或 RAG 流
```

`ChatService` 不保存用户会话。调用方传入历史，服务只负责裁剪最近十轮、校验角色、发起模型请求和返回增量文本。这样 CLI 可以继续维护自己的历史，Web API 也能为每个邀请码建立独立的浏览器会话。

## 二、邀请码不是前端密码框

如果只在 Vue 组件里判断：

```ts
if (input === '某个邀请码') {
  showChat = true
}
```

这只是界面隐藏，不是访问控制。用户仍然可以直接调用接口，或者从浏览器代码中找到邀请码。因此真正的校验必须发生在 FastAPI 服务器端。

这次采用了长期通行码模型：

- 每个邀请码可以在多台设备重复兑换。
- 兑换后得到 30 天 HttpOnly 会话 Cookie。
- 邀请码被撤销时，已有会话立即失效。
- 同一个邀请码的多台设备共享调用额度。

邀请码本身不写入数据库。服务器使用独立的 `INVITE_CODE_PEPPER` 计算 HMAC-SHA256：

```text
digest = HMAC-SHA256(INVITE_CODE_PEPPER, invite_code)
```

登录时再次计算摘要并查询数据库。即使 SQLite 文件泄露，攻击者也不会直接得到邀请码明文。Pepper 本身放在服务器环境变量中，不能提交 Git。

管理命令通过隐藏输入读取邀请码：

```powershell
python -m app.invite_admin create --label "本地测试"
```

邀请码要求 16–64 个字符，只允许字母、数字、`-` 和 `_`，并且至少包含字母和数字。忘记原码后无法从数据库恢复，只能撤销旧码并新建一个。

## 三、SQLite 记录什么，不记录什么

第一版使用 SQLite，原因是当前只有一台服务器和小规模受邀用户，不需要为了一个简单访问控制功能立即引入 PostgreSQL。

数据库包含四类数据：

| 数据 | 用途 | 是否保存聊天正文 |
|---|---|---|
| `invites` | 邀请码摘要、备注、状态和额度 | 否 |
| `sessions` | 会话令牌摘要和过期时间 | 否 |
| `usage_events` | 模式、时间、结果和耗时 | 否 |
| `login_attempts` | 登录失败频率限制 | 否 |

问题和回答只保存在当前浏览器的 `localStorage` 中，并按匿名访问者 ID 分开保存。主动退出时会清除对应的本地历史；服务器不保存完整对话，因此也没有“跨设备继续历史”的功能。

这是一种有意识的取舍：

- 好处是降低隐私和数据备份负担。
- 代价是清除浏览器数据后无法恢复历史。

## 四、限额必须在模型调用之前预占

默认额度为每个邀请码：

```text
5 次 / 分钟
50 次 / 24 小时
```

请求进入后，服务端先在 SQLite 事务中检查并预占一次用量，再开始调用模型。不能等模型回答完成后才计数，否则两个并发请求可能同时看到“还有额度”，最终超出限制。

同时，单进程内还限制同一个邀请码只能有一个正在生成的回答。这样可以避免用户快速打开多个标签页，造成并发模型请求和上下文混乱。

额度限制不是完整的计费系统，但它提供了最基本的安全阀。后续如果用户量增加，需要把这部分迁移到 Redis 或独立的限流服务。

## 五、为什么选择 SSE

普通 HTTP 接口可以一次性返回完整答案，但模型生成通常需要几秒甚至更久。Web Chat 需要让用户看到逐字出现的回答，因此后端使用 Server-Sent Events：

```text
event: token
data: {"text":"你好"}

event: token
data: {"text":"，我是 AI 助手。"}

event: done
data: {"requestId":"..."}
```

浏览器使用 `fetch` 读取 `ReadableStream`，自行解析 SSE 分块。这样请求体仍然可以使用 POST，适合同时发送当前问题、历史和 RAG 模式；也比把复杂上下文塞进只能 GET 的原生 `EventSource` 更灵活。

Nginx 对这条路径关闭代理缓冲：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;
    proxy_read_timeout 300s;
}
```

如果忘记 `proxy_buffering off`，后端虽然在流式发送，浏览器却可能积累一大段后才一次显示，体验上就像没有流式输出。

## 六、浏览器聊天界面的几个边界

当前页面提供：

- 邀请码输入、显示/隐藏和验证状态。
- 普通聊天 / RAG 模式切换。
- 多轮上下文、清空记录、退出登录。
- 生成过程中停止请求。
- 移动端布局。
- Markdown 展示。

模型输出不能直接当作可信 HTML 插入页面。当前流程是：

```text
Markdown 文本
  → markdown-it（禁用原始 HTML）
  → DOMPurify
  → v-html
```

服务端同样限制消息角色只能是 `user` 或 `assistant`，拒绝浏览器伪造 `system` 消息。前端校验是体验优化，后端校验才是安全边界。

## 七、本地到服务器的发布方式

项目采用 GitHub 作为源码中心：

```text
本地修改与测试
  → git commit
  → git push origin master
  → 服务器 git pull --ff-only
  → npm ci / pip install
  → VITEPRESS_BASE=/ npm run build
  → rsync 到 /var/www/chienzz.top
```

服务器不直接修改项目源码。Nginx 配置、systemd 单元和部署脚本模板也放进了 `deploy/`，但真正的 `/etc/ai-study/chat.env`、SQLite 数据库、证书和 API Key 都留在服务器。

生产服务使用专用的无登录用户 `ai-study`，Uvicorn 只监听 `127.0.0.1:8000`，公网只开放 Nginx 的 80/443 端口。备案和 HTTPS 完成后，Cookie 才会启用 `Secure` 属性。

## 测试结果

本次实现完成了三层验证：

- Python 后端 18 项测试：邀请码摘要、会话、撤销、过期、Cookie、双层额度、并发和 SSE。
- 前端 11 项测试：门禁、SSE 解析、本地历史隔离、Markdown 净化、RAG 切换、停止和退出。
- VitePress 根路径生产构建、部署脚本 Shell 语法和 Python 编译检查均通过。

当前还没有把真实 API Key 和生产邀请码写入本地或服务器，避免测试过程产生不可控的外部调用。备案通过后，再进行真实模型请求、HTTPS Cookie 和 Nginx SSE 的线上验收。

## 下一步

这次开发让我重新确认了一件事：把一个能运行的 Demo 变成可访问的服务，核心不是把代码“搬到服务器”，而是重新定义状态、身份、错误和数据边界。

下一步会在备案通过后完成：

1. 服务器安装 Python 3.12 和 Web Chat 运行依赖。
2. 配置生产环境变量、SQLite 数据目录和 `ai-study-chat.service`。
3. 安装 Nginx 配置并接入 HTTPS。
4. 生成第一个正式邀请码，验证普通聊天、RAG、额度和撤销流程。
5. 持续观察日志、备份数据库和控制模型调用成本。

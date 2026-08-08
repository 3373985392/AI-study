# 命令行与 Web 流式对话助手

基于 Python、OpenAI 兼容 SDK 和阿里云百炼 API 的命令行流式对话助手。

## 功能

- 流式输出模型回复
- 支持多轮上下文对话
- 支持 `/clear` 清空对话记忆
- 支持切换本地 RAG 知识库问答
- 支持 `/exit`、`/quit`、`/退出`、`/再见` 退出程序
- API 请求失败时不会直接退出
- FastAPI SSE 流式接口与 VitePress 浏览器聊天界面
- 长期邀请码、同步多会话、仅本机隐私会话、调用限额与来源展示
- 普通助手、Vue 框架助手和安全趣味人设
- 请求超时、有限重试、SSE 心跳以及无正文指标观测

## 环境要求

- Python 3.12
- 阿里云百炼 API Key
- 仓库根目录的共享虚拟环境 `D:\myproject\.venv`

## 安装

在仓库根目录创建并激活共享虚拟环境：

```powershell
cd D:\myproject
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
python -m pip install -r .\projects\cli-chat\requirements.txt
```

`cli-chat` 与 `minimal-rag` 共用根目录环境，不需要在项目目录中重复创建 `.venv`。

## 配置

在仓库根目录复制统一配置模板：

```powershell
cd D:\myproject
Copy-Item .env.example .env
```

编辑根目录的 `.env`，其中与普通聊天相关的配置为：

```dotenv
LLM_API_KEY=你的百炼API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
LLM_CONNECT_TIMEOUT_SECONDS=10
LLM_READ_TIMEOUT_SECONDS=60
LLM_MAX_OUTPUT_TOKENS=2048
LLM_MAX_RETRIES=2
LLM_CONTEXT_WINDOW_TOKENS=32768
# 默认复用 LLM_MODEL，无需额外部署记忆模型
# LLM_MEMORY_MODEL=qwen-plus
LLM_MEMORY_TRIGGER_TOKENS=16000
LLM_MEMORY_RECENT_ROUNDS=4
LLM_MEMORY_MAX_INPUT_TOKENS=12000
LLM_MEMORY_MAX_OUTPUT_TOKENS=800
```

普通同步会话会在上下文达到 `LLM_MEMORY_TRIGGER_TOKENS` 后，把较早消息
压缩为滚动摘要，同时保留最近若干轮原文。摘要调用默认复用聊天模型；原始
消息仍完整保存在数据库中。仅本机会话不在服务端生成或保存摘要。

不要把 `.env` 提交到 Git。

## 运行

```powershell
cd D:\myproject\projects\cli-chat
python chat.py
```

## 本地运行 Web Chat

先在仓库根目录 `.env` 中配置模型参数和 Web Chat 参数。邀请码、普通会话和
管理员会话使用的三个 Pepper 必须互不相同，且至少 32 个字符。

管理员后台还需要独立的会话 Pepper 和 scrypt 密码哈希。密码哈希通过隐藏输入生成：

```powershell
cd D:\myproject\projects\cli-chat
..\..\.venv\Scripts\python.exe -m app.admin_credentials hash
```

将输出写入 `ADMIN_PASSWORD_HASH`，并另外生成
`ADMIN_SESSION_TOKEN_PEPPER`。管理员页面地址为 `/admin`。

在第一个 PowerShell 窗口启动后端：

```powershell
cd D:\myproject\projects\cli-chat
..\..\.venv\Scripts\python.exe -m uvicorn app.web_api:create_app --factory --reload --port 8000
```

在第二个 PowerShell 窗口启动 VitePress：

```powershell
cd D:\myproject
$env:VITEPRESS_BASE = "/"
npm run dev
```

浏览器访问 `http://localhost:5173/chat`。VitePress 会将 `/api`
代理到本机的 FastAPI 服务。

Web 页面中的“Vue 框架助手”会自动使用 `minimal-rag`，不再需要单独选择
聊天模式。同步会话正文默认保留 365 天；选择“新会话仅本机”后，正文只会
进入当前浏览器的 `localStorage`，不会写入服务器数据库。

调用指标只记录模型、人设、结果、首 Token 延迟、总耗时、字符数、Token 数和
估算成本，不记录消息正文。为成本估算配置模型的每百万 Token 单价：

```dotenv
LLM_INPUT_PRICE_PER_MILLION=0
LLM_OUTPUT_PRICE_PER_MILLION=0
```

## 管理邀请码

邀请码明文只会在隐藏输入时出现，数据库中仅保存 HMAC 摘要：

```powershell
cd D:\myproject\projects\cli-chat
..\..\.venv\Scripts\python.exe -m app.invite_admin create --label "测试用户"
..\..\.venv\Scripts\python.exe -m app.invite_admin list
..\..\.venv\Scripts\python.exe -m app.invite_admin stats 邀请码ID
..\..\.venv\Scripts\python.exe -m app.invite_admin revoke 邀请码ID
..\..\.venv\Scripts\python.exe -m app.invite_admin activate 邀请码ID
```

邀请码必须为 16–64 位，只能包含字母、数字、`-` 和 `_`，并且至少
同时包含一个字母和一个数字。忘记的邀请码无法恢复，只能撤销后新建。

## 对话命令

```text
/rag on   开启 minimal-rag 知识库问答
/rag off  切回普通聊天模式
/clear    清空当前对话记忆
/exit     退出程序
/quit     退出程序
/退出     退出程序
/再见     退出程序
```

## RAG 模式

RAG 模式复用相邻的 `minimal-rag` 项目，两个项目应保持以下目录关系：

```text
projects/
├─ cli-chat/
└─ minimal-rag/
```

使用前需要确保 `minimal-rag/.env` 已配置，并且已经生成：

```text
minimal-rag/data/vectors.jsonl
```

RAG 模式只用当前问题进行向量检索，不会把整段聊天历史加入检索查询。
检索结果经过提示词构建后交给聊天模型，并以 `[来源 N]` 格式引用本地文档。

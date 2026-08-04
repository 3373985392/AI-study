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
- 长期邀请码、30 天会话、调用限额与本地历史隔离

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
```

不要把 `.env` 提交到 Git。

## 运行

```powershell
cd D:\myproject\projects\cli-chat
python chat.py
```

## 本地运行 Web Chat

先在仓库根目录 `.env` 中配置模型参数和 Web Chat 参数。两个 Pepper
必须使用不同的随机值，且至少 32 个字符。

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

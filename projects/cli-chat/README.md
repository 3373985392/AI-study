# 命令行流式对话助手

基于 Python、OpenAI 兼容 SDK 和阿里云百炼 API 的命令行流式对话助手。

## 功能

- 流式输出模型回复
- 支持多轮上下文对话
- 支持 `/clear` 清空对话记忆
- 支持 `/exit`、`/quit`、`/退出`、`/再见` 退出程序
- API 请求失败时不会直接退出

## 环境要求

- Python 3.10+
- 阿里云百炼 API Key

## 安装

进入项目目录：

```powershell
cd projects/cli-chat
```

创建并激活虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 配置

复制配置模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```dotenv
LLM_API_KEY=你的百炼API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

不要把 `.env` 提交到 Git。

## 运行

```powershell
python chat.py
```

## 对话命令

```text
/clear  清空当前对话记忆
/exit    退出程序
/quit    退出程序
/退出    退出程序
/再见    退出程序
```
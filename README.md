# AI Agent 开发学习仓库

这个仓库记录从 Python 后端开发转向 AI Agent 应用开发的学习过程，并通过可运行的小型项目逐步理解大模型调用、命令行交互、RAG、Agent、MCP 和工程部署。

仓库同时包含 VitePress 学习笔记站点和 Python 实践项目。当前已完成命令行聊天助手与最小 RAG，并将两者组合为可切换的本地知识库聊天程序。

## 当前项目

### CLI Chat

基于 OpenAI 兼容接口的中文命令行聊天助手，支持流式输出、多轮上下文、错误处理以及普通聊天与 RAG 模式切换。

项目说明：[projects/cli-chat/README.md](projects/cli-chat/README.md)

### Web Chat

站点的 `/chat` 页面复用 CLI Chat 的模型与 RAG 能力，使用服务端邀请码验证。
邀请码、会话和额度数据保存在服务器 SQLite 中，浏览器只保存当前邀请码对应的
本地聊天历史；API Key 不会发送到浏览器。开发和生产部署说明见
[projects/cli-chat/README.md](projects/cli-chat/README.md) 与 [deploy/README.md](deploy/README.md)。

### Minimal RAG

不使用 RAG 框架，从零实现以下完整链路：

```text
读取文档
→ 文档清洗与切分
→ Embedding
→ 向量持久化
→ 相似度与元数据混合检索
→ 提示词拼接
→ 带来源引用的流式回答
```

项目说明：[projects/minimal-rag/README.md](projects/minimal-rag/README.md)

## 项目关系

```text
用户
└─ projects/cli-chat/chat.py
   ├─ 普通模式 → 聊天模型与多轮历史
   └─ RAG 模式
      └─ projects/minimal-rag
         ├─ 查询向量化与本地检索
         ├─ 带编号来源的提示词
         └─ 聊天模型流式回答
```

`cli-chat` 负责用户交互，`minimal-rag` 负责知识库检索和基于资料生成答案。输入 `/rag on` 或 `/rag off` 可以在两种模式之间切换。

## 环境要求

- Python 3.12
- Node.js 20 或更高版本
- OpenAI 兼容的模型服务

所有 Python 项目统一使用仓库根目录的虚拟环境：

```text
D:\myproject\.venv
```

## Python 环境

创建并激活共享环境：

```powershell
cd D:\myproject
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装当前项目依赖：

```powershell
python -m pip install --upgrade pip
python -m pip install -r .\projects\cli-chat\requirements.txt
python -m pip install -r .\projects\minimal-rag\requirements.txt
```

两个 Python 项目分别维护依赖声明，但当前共用同一个运行环境。不要在各项目目录中重复创建 `.venv`。

## 运行组合应用

激活根目录环境后执行：

```powershell
cd D:\myproject\projects\cli-chat
python chat.py
```

常用命令：

```text
/rag on   开启 Vue 本地知识库问答
/rag off  切回普通聊天
/clear    清空对话历史
/exit     退出程序
```

普通聊天和 RAG 统一读取仓库根目录的 `.env`。可以从模板创建配置：

```powershell
cd D:\myproject
Copy-Item .env.example .env
```

`LLM_*` 用于普通聊天，`EMBEDDING_*` 与 `CHAT_MODEL` 用于 RAG。两组配置可以使用不同的 API Key 或接口地址，`.env` 不应提交到 Git。

## 学习笔记站点

在线访问：<https://chien-zz.github.io/AI-study/>

本地启动：

```powershell
cd D:\myproject
npm ci
npm run dev
```

生产构建与本地预览：

```powershell
npm run build
npm run preview
```

## 仓库结构

```text
.
├─ .github/workflows/       # GitHub Pages 部署工作流
├─ .env.example             # 所有 Python 项目共用的配置模板
├─ .venv/                   # 所有 Python 项目共用的本地虚拟环境
├─ .vitepress/              # VitePress 配置与主题
├─ blog/posts/              # 学习笔记与博客文章
├─ projects/
│  ├─ cli-chat/             # 流式命令行聊天助手
│  └─ minimal-rag/          # 从零实现的最小 RAG
├─ public/                  # 站点静态资源
├─ about.md                 # 站点关于页面
├─ index.md                 # 站点首页
└─ package.json             # VitePress 脚本与依赖
```

## 配置与数据安全

- `.env`、根目录 `.venv`、Python 缓存和 Node.js 依赖已通过 `.gitignore` 排除
- 不要在命令输出、截图、文档或提交记录中暴露 API Key
- `minimal-rag/sources/` 保存外部语料原仓库和许可证，不作为自己的原创内容发布
- 重新生成向量前，应确认 Embedding 模型和输入格式没有意外变化

## 发布学习站点

推送到 `master` 分支后，GitHub Actions 会构建站点并部署到 GitHub Pages。仓库的 Pages Source 需要设置为 **GitHub Actions**。

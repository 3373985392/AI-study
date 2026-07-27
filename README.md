# AI Agent 开发笔记

记录从 Python 后端开发转向 AI Agent 应用开发的学习过程，包括 RAG、LangChain、LangGraph、MCP 和工程部署等主题。

## 在线访问

<https://3373985392.github.io/AI-study/>

## 本地开发

需要 Node.js 20 或更高版本。

```bash
npm ci
npm run dev
```

生产构建与本地预览：

```bash
npm run build
npm run preview
```

## 目录结构

```text
.
├── .github/workflows/   # GitHub Pages 部署工作流
├── .vitepress/          # VitePress 配置与主题样式
├── blog/posts/          # 博客文章
├── public/              # 静态资源
├── about.md             # 关于页面
└── index.md             # 站点首页
```

## 发布

推送到 `master` 分支后，GitHub Actions 会构建站点并部署到 GitHub Pages。仓库的 Pages Source 需要设置为 **GitHub Actions**。

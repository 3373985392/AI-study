import { defineConfig } from 'vitepress'

// 部署路径模块：GitHub Pages 默认使用仓库子路径，独立域名构建时可通过环境变量切换为根路径。
const BASE = process.env.VITEPRESS_BASE ?? '/AI-study/'

export default defineConfig({
  base: BASE,

  // 本地开发代理模块：浏览器始终请求同源 /api，生产环境由 Nginx 接管相同路径。
  vite: {
    server: {
      // 开发服务器只绑定回环地址，避免将调试接口意外暴露到局域网。
      host: '127.0.0.1',
      strictPort: true,
      proxy: {
        '/api': 'http://127.0.0.1:8000',
      },
    },
  },

  // 仓库说明、项目 README 与 RAG 语料不是站点页面，避免 VitePress 解析其资源引用。
  srcExclude: ['README.md', 'projects/**', 'deploy/**'],

  title: 'AI Agent 开发笔记',
  description: 'Python后端转AI Agent开发者的技术博客',
  lang: 'zh-CN',

  cleanUrls: true,

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${BASE}favicon.svg` }],
    ['meta', { name: 'author', content: 'ZhuanZ' }],
  ],

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: 'AI Chat', link: '/chat' },
      { text: '博客', link: '/blog/' },
      { text: '标签', link: '/blog/tags' },
      { text: '关于', link: '/about' },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/chien-zZ' },
    ],

    footer: {
      message: '基于 VitePress 构建',
      copyright: `Copyright © ${new Date().getFullYear()} ZhuanZ`,
    },

    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索' },
          modal: { noResultsText: '没有找到结果' },
        },
      },
    },

    outline: {
      level: [2, 3],
      label: '目录',
    },

    docFooter: {
      prev: '上一篇',
      next: '下一篇',
    },

    lastUpdated: {
      text: '最后更新于',
    },

    editLink: {
      pattern: 'https://github.com/chien-zZ/AI-study/edit/master/:path',
      text: '在 GitHub 上编辑此页',
    },
  },

  markdown: {
    lineNumbers: true,
  },
})

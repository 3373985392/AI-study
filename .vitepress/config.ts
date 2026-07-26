import { defineConfig } from 'vitepress'

const BASE = '/AI-study/'

export default defineConfig({
  base: BASE,

  title: 'AI Agent 开发笔记',
  description: 'Python后端转AI Agent开发者的技术博客',
  lang: 'zh-CN',

  cleanUrls: true,

  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
    ['meta', { name: 'author', content: 'ZhuanZ' }],
  ],

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '博客', link: '/blog/' },
      { text: '标签', link: '/blog/tags' },
      { text: '关于', link: '/about' },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/3373985392' },
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
      pattern: 'https://github.com/3373985392/AI-study/edit/master/:path',
      text: '在 GitHub 上编辑此页',
    },
  },

  markdown: {
    lineNumbers: true,
  },
})

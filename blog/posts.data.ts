import { createContentLoader } from 'vitepress'

export interface Post {
  title: string
  url: string
  date: string
  formattedDate: string
  tags: string[]
  categories: string[]
  excerpt: string
  readingTime: number
}

declare const data: Post[]
export { data }

export default createContentLoader('blog/posts/*.md', {
  excerpt: true,
  transform(raw): Post[] {
    return raw
      .map((page) => {
        const fm = page.frontmatter
        const words = page.excerpt?.length || 0
        return {
          title: fm.title as string,
          url: page.url,
          date: fm.date as string,
          formattedDate: formatChineseDate(fm.date as string),
          tags: (fm.tags as string[]) || [],
          categories: (fm.categories as string[]) || [],
          excerpt: page.excerpt || '',
          readingTime: Math.max(1, Math.ceil(words / 300)),
        }
      })
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  },
})

function formatChineseDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

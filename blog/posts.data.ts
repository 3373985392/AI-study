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
  transform(raw): Post[] {
    return raw
      .map((page) => {
        const fm = page.frontmatter
        return {
          title: fm.title as string,
          url: page.url,
          date: fm.date as string,
          formattedDate: formatChineseDate(fm.date as string),
          tags: (fm.tags as string[]) || [],
          categories: (fm.categories as string[]) || [],
          excerpt: (fm.description as string) || '',
          readingTime: 0,
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

/** 将模型 Markdown 转成经过净化的 HTML，禁止模型直接注入 HTML。 */

import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'


const markdown = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
})

export function renderMarkdown(content: string): string {
  return DOMPurify.sanitize(markdown.render(content), {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'iframe', 'form', 'input', 'button'],
    FORBID_ATTR: ['style'],
  })
}


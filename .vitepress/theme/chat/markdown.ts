/** 将模型 Markdown 转成经过净化的 HTML，禁止模型直接注入 HTML。 */

import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'


const markdown = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
})

const defaultFence = markdown.renderer.rules.fence?.bind(markdown.renderer.rules)
markdown.renderer.rules.fence = (tokens, index, options, env, self) => {
  const rendered = defaultFence
    ? defaultFence(tokens, index, options, env, self)
    : self.renderToken(tokens, index, options)
  return `<div class="code-block"><button type="button" class="code-copy" aria-label="复制代码">复制</button>${rendered}</div>`
}

export function renderMarkdown(content: string): string {
  return DOMPurify.sanitize(markdown.render(content), {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'iframe', 'form', 'input'],
    FORBID_ATTR: ['style'],
  })
}

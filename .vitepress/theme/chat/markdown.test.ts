import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'


describe('safe markdown', () => {
  it('renders markdown while removing executable html', () => {
    const html = renderMarkdown('**安全文本** <img src=x onerror=alert(1)>')

    expect(html).toContain('<strong>安全文本</strong>')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })
})

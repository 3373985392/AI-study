import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, streamReply } from './api'


afterEach(() => vi.unstubAllGlobals())

describe('streamReply', () => {
  it('parses tokens, Vue sources and persisted messages across chunks', async () => {
    const encoder = new TextEncoder()
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('event: sources\ndata: {"items":[{"file":"docs/watchers.md","documentTitle":"侦听器","sectionTitle":"基本示例","score":0.9,"url":"https://example.com"}]}\n\n'))
        controller.enqueue(encoder.encode('event: token\ndata: {"text":"你"}\n'))
        controller.enqueue(encoder.encode('\nevent: token\ndata: {"text":"好"}\n\n'))
        controller.enqueue(encoder.encode('event: done\ndata: {"requestId":"r1","messages":[{"id":"u1","role":"user","content":"测试"},{"id":"a1","role":"assistant","content":"你好"}]}\n\n'))
        controller.close()
      },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })))
    const tokens: string[] = []
    const sources: string[] = []

    const result = await streamReply({
      message: '测试', history: [], persona: 'vue', conversationId: 'c1',
      signal: new AbortController().signal,
      onToken: (text) => tokens.push(text),
      onSources: (items) => sources.push(items[0].file),
    })

    expect(tokens).toEqual(['你', '好'])
    expect(sources).toEqual(['docs/watchers.md'])
    expect(result.messages.map((item) => item.id)).toEqual(['u1', 'a1'])
  })

  it('exposes retry delay for quota responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: '额度已用完' }),
      { status: 429, headers: { 'Content-Type': 'application/json', 'Retry-After': '42' } },
    )))
    await expect(streamReply({
      message: '测试', history: [], persona: 'normal', signal: new AbortController().signal,
      onToken: () => undefined,
    })).rejects.toMatchObject<ApiError>({ status: 429, retryAfter: 42 })
  })
})

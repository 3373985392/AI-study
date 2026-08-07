import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, streamReply } from './api'


afterEach(() => vi.unstubAllGlobals())

describe('streamReply', () => {
  it('parses SSE tokens split across network chunks', async () => {
    const encoder = new TextEncoder()
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('event: token\ndata: {"text":"你"}\n'))
        controller.enqueue(encoder.encode('\nevent: token\ndata: {"text":"好"}\n\n'))
        controller.enqueue(encoder.encode('event: done\ndata: {"requestId":"r1"}\n\n'))
        controller.close()
      },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })))
    const tokens: string[] = []

    await streamReply({
      message: '测试',
      history: [],
      mode: 'chat',
      persona: 'brat',
      signal: new AbortController().signal,
      onToken: (text) => tokens.push(text),
    })

    expect(tokens).toEqual(['你', '好'])
  })

  it('exposes retry delay for quota responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: '额度已用完' }),
      { status: 429, headers: { 'Content-Type': 'application/json', 'Retry-After': '42' } },
    )))

    await expect(streamReply({
      message: '测试',
      history: [],
      mode: 'chat',
      persona: 'normal',
      signal: new AbortController().signal,
      onToken: () => undefined,
    })).rejects.toMatchObject<ApiError>({ status: 429, retryAfter: 42 })
  })
})

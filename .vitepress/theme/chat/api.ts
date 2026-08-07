/** 浏览器与同源 FastAPI 后端之间的唯一通信模块。 */

import type { AuthState, ChatMessage, ChatMode, PersonaId } from './types'


export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly retryAfter?: number,
  ) {
    super(message)
  }
}

async function parseError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => ({})) as { detail?: string }
  const retryAfter = Number(response.headers.get('Retry-After')) || undefined
  return new ApiError(body.detail || '请求失败，请稍后重试', response.status, retryAfter)
}

export async function getSession(): Promise<AuthState> {
  const response = await fetch('/api/auth/session', { credentials: 'same-origin' })
  if (!response.ok) throw await parseError(response)
  return response.json()
}

export async function redeemInvite(code: string): Promise<AuthState> {
  const response = await fetch('/api/auth/redeem', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })
  if (!response.ok) throw await parseError(response)
  return response.json()
}

export async function logoutSession(): Promise<void> {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
  })
  if (!response.ok) throw await parseError(response)
}

interface StreamOptions {
  message: string
  history: ChatMessage[]
  mode: ChatMode
  persona: PersonaId
  signal: AbortSignal
  onToken: (text: string) => void
}

export async function streamReply(options: StreamOptions): Promise<void> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: options.message,
      history: options.history,
      mode: options.mode,
      persona: options.persona,
    }),
    signal: options.signal,
  })
  if (!response.ok) throw await parseError(response)
  if (!response.body) throw new ApiError('浏览器不支持流式响应', 0)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // SSE 解析模块：保留不完整分块，直到收到空行分隔的完整事件。
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n')
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const block of events) {
      const event = block.match(/^event: (.+)$/m)?.[1]
      const rawData = block.match(/^data: (.+)$/m)?.[1]
      if (!event || !rawData) continue
      const data = JSON.parse(rawData) as { text?: string; message?: string }
      if (event === 'token' && data.text) options.onToken(data.text)
      if (event === 'error') throw new ApiError(data.message || '生成回答失败', 0)
    }
    if (done) break
  }
}

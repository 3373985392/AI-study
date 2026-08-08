/** 浏览器与同源 FastAPI 后端之间的唯一通信模块。 */

import type { AuthState, ChatMessage, ChatSource, Conversation, PersonaId } from './types'


export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly retryAfter?: number,
    public readonly code?: string,
  ) {
    super(message)
  }
}

async function parseError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => ({})) as { detail?: string; code?: string }
  const retryAfter = Number(response.headers.get('Retry-After')) || undefined
  return new ApiError(body.detail || '请求失败，请稍后重试', response.status, retryAfter, body.code)
}

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { credentials: 'same-origin', ...init })
  if (!response.ok) throw await parseError(response)
  return response.json()
}

async function requestEmpty(url: string, init: RequestInit): Promise<void> {
  const response = await fetch(url, { credentials: 'same-origin', ...init })
  if (!response.ok) throw await parseError(response)
}

export function getSession(): Promise<AuthState> {
  return requestJson('/api/auth/session')
}

export function redeemInvite(code: string): Promise<AuthState> {
  return requestJson('/api/auth/redeem', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })
}

export function logoutSession(): Promise<void> {
  return requestEmpty('/api/auth/logout', { method: 'POST' })
}

export function listConversations(): Promise<Conversation[]> {
  return requestJson('/api/conversations')
}

export function createConversation(persona: PersonaId): Promise<Conversation> {
  return requestJson('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona }),
  })
}

export function updateConversation(
  conversationId: string,
  changes: { title?: string; persona?: PersonaId },
): Promise<Conversation> {
  return requestJson(`/api/conversations/${conversationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
}

export function deleteConversation(conversationId: string): Promise<void> {
  return requestEmpty(`/api/conversations/${conversationId}`, { method: 'DELETE' })
}

export function listMessages(conversationId: string): Promise<ChatMessage[]> {
  return requestJson(`/api/conversations/${conversationId}/messages`)
}

export function deleteMessage(messageId: string): Promise<void> {
  return requestEmpty(`/api/messages/${messageId}`, { method: 'DELETE' })
}

export function sendFeedback(messageId: string, rating: -1 | 1, comment?: string): Promise<void> {
  return requestEmpty(`/api/messages/${messageId}/feedback`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating, comment }),
  })
}

interface StreamOptions {
  message: string
  history: ChatMessage[]
  persona: PersonaId
  conversationId?: string
  signal: AbortSignal
  onToken: (text: string) => void
  onSources?: (sources: ChatSource[]) => void
}

export interface StreamResult {
  requestId?: string
  messages: ChatMessage[]
}

export async function streamReply(options: StreamOptions): Promise<StreamResult> {
  let response: Response
  try {
    response = await fetch('/api/chat/stream', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: options.message,
        history: options.history,
        persona: options.persona,
        conversation_id: options.conversationId,
      }),
      signal: options.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('无法连接聊天服务，请检查网络后重试', 0, undefined, 'network_error')
  }
  if (!response.ok) throw await parseError(response)
  if (!response.body) throw new ApiError('浏览器不支持流式响应', 0)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result: StreamResult = { messages: [] }

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
      const data = JSON.parse(rawData) as {
        text?: string
        message?: string
        code?: string
        requestId?: string
        messages?: ChatMessage[]
        items?: ChatSource[]
      }
      if (event === 'token' && data.text) options.onToken(data.text)
      if (event === 'sources' && data.items) options.onSources?.(data.items)
      if (event === 'done') result = { requestId: data.requestId, messages: data.messages || [] }
      if (event === 'error') throw new ApiError(data.message || '生成回答失败', 0, undefined, data.code)
    }
    if (done) break
  }
  return result
}

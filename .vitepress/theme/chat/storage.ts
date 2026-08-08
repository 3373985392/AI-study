/** 浏览器隐私会话模块：仅保存用户明确选择“仅本机”的会话。 */

import type { ChatMessage, Conversation, PersonaId } from './types'


const KEY_PREFIX = 'ai-study-local-conversations:v2:'
const ACTIVE_KEY_PREFIX = 'ai-study-active-conversation:v2:'
const MAX_MESSAGES = 20
const MAX_MESSAGE_CHARACTERS = 12_000
const MAX_HISTORY_CHARACTERS = 40_000

function key(viewerId: string): string {
  return `${KEY_PREFIX}${viewerId}`
}

export function prepareHistory(history: ChatMessage[]): ChatMessage[] {
  const prepared = history.slice(-MAX_MESSAGES).map((message) => ({
    role: message.role,
    content: message.content.slice(0, MAX_MESSAGE_CHARACTERS),
  }))
  while (
    prepared.length > 0 &&
    prepared.reduce((total, message) => total + message.content.length, 0) > MAX_HISTORY_CHARACTERS
  ) {
    // 每次移除最旧的一轮，避免请求上下文留下孤立回答。
    prepared.splice(0, Math.min(2, prepared.length))
  }
  return prepared
}

export function createLocalConversation(persona: PersonaId): Conversation {
  const now = Math.floor(Date.now() / 1000)
  const randomId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`
  return {
    id: `local-${randomId}`,
    title: '新对话',
    persona,
    localOnly: true,
    createdAt: now,
    updatedAt: now,
    messages: [],
  }
}

export function loadLocalConversations(viewerId: string): Conversation[] {
  try {
    const value = JSON.parse(localStorage.getItem(key(viewerId)) || '[]')
    if (!Array.isArray(value)) return []
    return value.filter((item) => (
      item && typeof item.id === 'string' && item.id.startsWith('local-') &&
      typeof item.title === 'string' && ['normal', 'vue', 'brat'].includes(item.persona) &&
      Array.isArray(item.messages)
    )).map((item) => ({ ...item, localOnly: true }))
  } catch {
    return []
  }
}

export function saveLocalConversations(viewerId: string, conversations: Conversation[]): void {
  const local = conversations.filter((item) => item.localOnly).map((item) => ({
    ...item,
    messages: (item.messages || []).slice(-MAX_MESSAGES),
  }))
  try {
    localStorage.setItem(key(viewerId), JSON.stringify(local))
  } catch {
    // 浏览器空间不足时保留会话元数据和最近四轮，避免发送流程被存储异常打断。
    const compact = local.map((item) => ({ ...item, messages: (item.messages || []).slice(-8) }))
    try { localStorage.setItem(key(viewerId), JSON.stringify(compact)) } catch { /* 本机存储不可用 */ }
  }
}

export function loadActiveConversationId(viewerId: string): string {
  return localStorage.getItem(`${ACTIVE_KEY_PREFIX}${viewerId}`) || ''
}

export function saveActiveConversationId(viewerId: string, conversationId: string): void {
  localStorage.setItem(`${ACTIVE_KEY_PREFIX}${viewerId}`, conversationId)
}

// 兼容旧版本导出，供迁移期间已有调用和测试安全清理历史。
export function clearHistory(viewerId: string): void {
  localStorage.removeItem(key(viewerId))
  localStorage.removeItem(`${ACTIVE_KEY_PREFIX}${viewerId}`)
}

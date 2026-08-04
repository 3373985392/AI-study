/** 仅在当前浏览器保存聊天正文；邀请码和会话令牌不会进入 localStorage。 */

import type { ChatMessage } from './types'


const KEY_PREFIX = 'ai-study-chat-history:v1:'
const MAX_MESSAGES = 20
const MAX_MESSAGE_CHARACTERS = 12_000
const MAX_HISTORY_CHARACTERS = 40_000

function key(viewerId: string): string {
  return `${KEY_PREFIX}${viewerId}`
}

export function loadHistory(viewerId: string): ChatMessage[] {
  try {
    const value = JSON.parse(localStorage.getItem(key(viewerId)) || '[]')
    if (!Array.isArray(value)) return []
    return prepareHistory(value
      .filter((item) => (
        item &&
        (item.role === 'user' || item.role === 'assistant') &&
        typeof item.content === 'string' &&
        item.content.length > 0
      )))
  } catch {
    return []
  }
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
    // 每次移除最旧的一轮，避免留下孤立的回答消息。
    prepared.splice(0, Math.min(2, prepared.length))
  }
  return prepared
}

export function saveHistory(viewerId: string, history: ChatMessage[]): void {
  let prepared = prepareHistory(history)
  while (prepared.length > 0) {
    try {
      localStorage.setItem(key(viewerId), JSON.stringify(prepared))
      return
    } catch {
      prepared = prepared.slice(Math.min(2, prepared.length))
    }
  }
  localStorage.removeItem(key(viewerId))
}

export function clearHistory(viewerId: string): void {
  localStorage.removeItem(key(viewerId))
}

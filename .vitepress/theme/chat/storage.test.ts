import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearHistory, createLocalConversation, loadActiveConversationId, loadLocalConversations,
  prepareHistory, saveActiveConversationId, saveLocalConversations,
} from './storage'


beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('crypto', { randomUUID: () => 'local-id' })
})

describe('local conversation storage', () => {
  it('stores only local conversations and isolates viewers', () => {
    const local = createLocalConversation('vue')
    local.messages = Array.from({ length: 24 }, (_, index) => ({
      role: index % 2 === 0 ? 'user' as const : 'assistant' as const,
      content: `message-${index}`,
    }))
    saveLocalConversations('viewer-a', [local, { ...local, id: 'remote-id', localOnly: false }])

    expect(loadLocalConversations('viewer-a')).toHaveLength(1)
    expect(loadLocalConversations('viewer-a')[0].messages).toHaveLength(20)
    expect(loadLocalConversations('viewer-b')).toEqual([])
  })

  it('stores and clears the active conversation per viewer', () => {
    saveActiveConversationId('viewer-a', 'conversation-a')
    expect(loadActiveConversationId('viewer-a')).toBe('conversation-a')

    clearHistory('viewer-a')
    expect(loadActiveConversationId('viewer-a')).toBe('')
  })

  it('caps individual messages and total request history', () => {
    const oversized = Array.from({ length: 20 }, (_, index) => ({
      role: index % 2 === 0 ? 'user' as const : 'assistant' as const,
      content: 'x'.repeat(12_500),
    }))
    const prepared = prepareHistory(oversized)
    expect(prepared.every((message) => message.content.length <= 12_000)).toBe(true)
    expect(prepared.reduce((total, message) => total + message.content.length, 0)).toBeLessThanOrEqual(40_000)
  })
})

import { beforeEach, describe, expect, it } from 'vitest'
import { clearHistory, loadHistory, prepareHistory, saveHistory } from './storage'


beforeEach(() => localStorage.clear())

describe('browser history', () => {
  it('isolates messages by viewer id and keeps ten rounds', () => {
    const messages = Array.from({ length: 24 }, (_, index) => ({
      role: index % 2 === 0 ? 'user' as const : 'assistant' as const,
      content: `message-${index}`,
    }))

    saveHistory('viewer-a', messages)

    expect(loadHistory('viewer-a')).toHaveLength(20)
    expect(loadHistory('viewer-b')).toEqual([])
    expect(loadHistory('viewer-a')[0].content).toBe('message-4')
  })

  it('clears only the selected viewer history', () => {
    saveHistory('viewer-a', [{ role: 'user', content: 'A' }])
    saveHistory('viewer-b', [{ role: 'user', content: 'B' }])

    clearHistory('viewer-a')

    expect(loadHistory('viewer-a')).toEqual([])
    expect(loadHistory('viewer-b')).toHaveLength(1)
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

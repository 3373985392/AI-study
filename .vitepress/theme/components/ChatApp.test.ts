import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ChatApp from './ChatApp.vue'
import { getSession, logoutSession, streamReply } from '../chat/api'


vi.mock('../chat/api', async () => {
  class ApiError extends Error {
    constructor(
      message: string,
      public status = 0,
      public retryAfter: number | undefined = undefined,
    ) {
      super(message)
    }
  }
  return {
    ApiError,
    getSession: vi.fn(),
    redeemInvite: vi.fn(),
    logoutSession: vi.fn(),
    streamReply: vi.fn(),
  }
})

beforeEach(() => {
  vi.mocked(getSession).mockReset()
  vi.mocked(streamReply).mockReset()
  vi.mocked(logoutSession).mockReset().mockResolvedValue(undefined)
  localStorage.clear()
})

function authenticatedSession() {
  vi.mocked(getSession).mockResolvedValue({
    authenticated: true,
    viewerId: 'viewer-1',
    expiresAt: 123,
    limits: { minute: 5, day: 50, minuteRemaining: 4, dayRemaining: 49 },
  })
}

describe('ChatApp authentication gate', () => {
  it('shows only the invite form when unauthenticated', async () => {
    vi.mocked(getSession).mockResolvedValue({ authenticated: false })

    const wrapper = mount(ChatApp)
    await flushPromises()

    expect(wrapper.text()).toContain('请输入邀请码继续')
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('loads the chat interface and local history after authentication', async () => {
    localStorage.setItem(
      'ai-study-chat-history:v1:viewer-1',
      JSON.stringify([{ role: 'user', content: '已保存的问题' }]),
    )
    authenticatedSession()

    const wrapper = mount(ChatApp)
    await flushPromises()

    expect(wrapper.text()).toContain('已保存的问题')
    expect(wrapper.text()).toContain('今日 49')
    expect(wrapper.find('textarea').exists()).toBe(true)
  })

  it('defaults to 雌小鬼 persona and keeps RAG disabled', async () => {
    authenticatedSession()
    vi.mocked(streamReply).mockImplementation(async (options) => {
      options.onToken('角色回答')
    })
    const wrapper = mount(ChatApp)
    await flushPromises()

    const modeButtons = wrapper.findAll('.mode-switch button')
    expect(modeButtons[0].text()).toBe('雌小鬼')
    expect(modeButtons[1].text()).toBe('普通')
    expect(modeButtons[2].attributes('disabled')).toBeDefined()
    await wrapper.find('textarea').setValue('你好')
    await wrapper.find('.send-button').trigger('click')
    await flushPromises()

    expect(streamReply).toHaveBeenCalledWith(expect.objectContaining({ mode: 'chat', persona: 'brat' }))
    expect(wrapper.text()).toContain('角色回答')
  })

  it('clears history when switching persona', async () => {
    localStorage.setItem(
      'ai-study-chat-history:v1:viewer-1',
      JSON.stringify([{ role: 'user', content: '旧角色历史' }]),
    )
    authenticatedSession()
    const wrapper = mount(ChatApp)
    await flushPromises()

    await wrapper.findAll('.mode-switch button')[1].trigger('click')

    expect(wrapper.text()).not.toContain('旧角色历史')
    expect(localStorage.getItem('ai-study-chat-history:v1:viewer-1')).toBeNull()
    expect(wrapper.text()).toContain('有什么想问的？')
  })

  it('aborts an active request when the stop button is pressed', async () => {
    authenticatedSession()
    let receivedSignal: AbortSignal | undefined
    vi.mocked(streamReply).mockImplementation((options) => {
      receivedSignal = options.signal
      return new Promise((_, reject) => {
        options.signal.addEventListener('abort', () => {
          reject(new DOMException('aborted', 'AbortError'))
        })
      })
    })
    const wrapper = mount(ChatApp)
    await flushPromises()
    await wrapper.find('textarea').setValue('停止测试')
    await wrapper.find('.send-button').trigger('click')
    await flushPromises()

    await wrapper.find('.stop-button').trigger('click')
    await flushPromises()

    expect(receivedSignal?.aborted).toBe(true)
    expect(wrapper.text()).toContain('已停止生成')
  })

  it('clears local history when the user logs out', async () => {
    localStorage.setItem(
      'ai-study-chat-history:v1:viewer-1',
      JSON.stringify([{ role: 'user', content: '私密内容' }]),
    )
    authenticatedSession()
    const wrapper = mount(ChatApp)
    await flushPromises()

    await wrapper.findAll('.header-actions button')[1].trigger('click')
    await flushPromises()

    expect(logoutSession).toHaveBeenCalledOnce()
    expect(localStorage.getItem('ai-study-chat-history:v1:viewer-1')).toBeNull()
    expect(wrapper.text()).toContain('请输入邀请码继续')
  })
})

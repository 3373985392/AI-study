import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminApp from './AdminApp.vue'
import {
  createAdminInvite, getAdminSession, listAdminConversations, listAdminInvites,
  listAdminMessages, loginAdmin, logoutAdmin, updateAdminInvite,
} from '../admin/api'


vi.mock('../admin/api', async () => {
  class AdminApiError extends Error {
    constructor(message: string, public status = 0, public retryAfter?: number) { super(message) }
  }
  return {
    AdminApiError,
    getAdminSession: vi.fn(), loginAdmin: vi.fn(), logoutAdmin: vi.fn(),
    listAdminInvites: vi.fn(), createAdminInvite: vi.fn(), updateAdminInvite: vi.fn(),
    listAdminConversations: vi.fn(), listAdminMessages: vi.fn(),
  }
})

const invite = {
  id: 'invite-1', label: '朋友A', active: true, minuteLimit: 5, dayLimit: 50,
  createdAt: 1, conversationCount: 1, totalUsed: 2, inputTokens: 10,
  outputTokens: 20, estimatedCostUsd: 0,
}
const conversation = {
  id: 'conversation-1', title: '测试会话', persona: 'normal' as const,
  createdAt: 1, updatedAt: 2, messageCount: 2,
}

beforeEach(() => {
  vi.mocked(getAdminSession).mockReset()
  vi.mocked(loginAdmin).mockReset().mockResolvedValue({ authenticated: true, expiresAt: 123 })
  vi.mocked(logoutAdmin).mockReset().mockResolvedValue(undefined)
  vi.mocked(listAdminInvites).mockReset().mockResolvedValue({ items: [invite], page: 1, pageSize: 30, total: 1 })
  vi.mocked(listAdminConversations).mockReset().mockResolvedValue({
    invite: { id: invite.id, label: invite.label, active: true },
    items: [conversation], page: 1, pageSize: 30, total: 1,
  })
  vi.mocked(listAdminMessages).mockReset().mockResolvedValue({
    conversation: { ...conversation, inviteId: invite.id, inviteLabel: invite.label },
    memory: { summary: '历史摘要', facts: [], decisions: [], openItems: [], updatedAt: 2 },
    items: [{ id: 'm1', role: 'user', content: '管理员可见正文', sources: [], createdAt: 1 }],
    page: 1, pageSize: 100, total: 1,
  })
  vi.mocked(createAdminInvite).mockReset().mockResolvedValue({ invite, oneTimeCode: 'GeneratedInvite2026_A' })
  vi.mocked(updateAdminInvite).mockReset().mockResolvedValue(invite)
})

describe('AdminApp', () => {
  it('shows an isolated administrator login when unauthenticated', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({ authenticated: false })
    const wrapper = mount(AdminApp)
    await flushPromises()

    expect(wrapper.text()).toContain('管理员后台')
    expect(wrapper.find('#admin-password').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('朋友A')
  })

  it('loads invite, conversation, messages and memory after authentication', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({ authenticated: true, expiresAt: 123 })
    const wrapper = mount(AdminApp)
    await flushPromises()

    expect(wrapper.text()).toContain('朋友A')
    await wrapper.find('.invite-panel .list-item').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('测试会话')
    await wrapper.find('.conversation-panel .list-item').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('管理员可见正文')
    expect(wrapper.text()).toContain('滚动记忆摘要')
  })

  it('creates an invite and displays its plaintext only once in the panel', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({ authenticated: true, expiresAt: 123 })
    const wrapper = mount(AdminApp)
    await flushPromises()
    await wrapper.find('.admin-toolbar > button').trigger('click')
    await wrapper.find('.create-panel input').setValue('新朋友')
    await wrapper.find('.create-panel').trigger('submit')
    await flushPromises()

    expect(createAdminInvite).toHaveBeenCalledWith(expect.objectContaining({ mode: 'generated', label: '新朋友' }))
    expect(wrapper.text()).toContain('GeneratedInvite2026_A')
    expect(wrapper.text()).toContain('仅显示这一次')
  })
})

/** 管理员后台专用 API；不与普通聊天认证和类型混用。 */

import type {
  AdminAuthState, AdminConversation, AdminInvite, AdminMemory, AdminMessage, Page,
} from './types'


export class AdminApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly retryAfter?: number) {
    super(message)
  }
}

async function parseError(response: Response): Promise<AdminApiError> {
  const body = await response.json().catch(() => ({})) as { detail?: string }
  return new AdminApiError(
    body.detail || '管理员请求失败',
    response.status,
    Number(response.headers.get('Retry-After')) || undefined,
  )
}

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', ...init })
  if (!response.ok) throw await parseError(response)
  return response.json()
}

async function requestEmpty(url: string, init: RequestInit): Promise<void> {
  const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', ...init })
  if (!response.ok) throw await parseError(response)
}

export function getAdminSession(): Promise<AdminAuthState> {
  return requestJson('/api/admin/auth/session')
}

export function loginAdmin(password: string): Promise<AdminAuthState> {
  return requestJson('/api/admin/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }),
  })
}

export function logoutAdmin(): Promise<void> {
  return requestEmpty('/api/admin/auth/logout', { method: 'POST' })
}

export function listAdminInvites(params: {
  query: string; status: 'all' | 'active' | 'revoked'; page: number; pageSize?: number
}): Promise<Page<AdminInvite>> {
  const query = new URLSearchParams({
    query: params.query, status: params.status, page: String(params.page),
    page_size: String(params.pageSize || 30),
  })
  return requestJson(`/api/admin/invites?${query}`)
}

export function createAdminInvite(payload: {
  mode: 'generated' | 'custom'; label: string; minuteLimit: number; dayLimit: number;
  code?: string; codeConfirmation?: string
}): Promise<{ invite: AdminInvite; oneTimeCode: string }> {
  return requestJson('/api/admin/invites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mode: payload.mode,
      label: payload.label,
      minute_limit: payload.minuteLimit,
      day_limit: payload.dayLimit,
      code: payload.code,
      code_confirmation: payload.codeConfirmation,
    }),
  })
}

export function updateAdminInvite(
  inviteId: string,
  changes: { label?: string; minuteLimit?: number; dayLimit?: number; active?: boolean },
): Promise<AdminInvite> {
  return requestJson(`/api/admin/invites/${inviteId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      label: changes.label,
      minute_limit: changes.minuteLimit,
      day_limit: changes.dayLimit,
      active: changes.active,
    }),
  })
}

export function listAdminConversations(
  inviteId: string, page: number, pageSize = 30,
): Promise<Page<AdminConversation> & { invite: { id: string; label: string; active: boolean } }> {
  return requestJson(`/api/admin/invites/${inviteId}/conversations?page=${page}&page_size=${pageSize}`)
}

export function listAdminMessages(
  conversationId: string, page: number, pageSize = 100,
): Promise<Page<AdminMessage> & {
  conversation: AdminConversation & { inviteId: string; inviteLabel: string }
  memory?: AdminMemory
}> {
  return requestJson(`/api/admin/conversations/${conversationId}/messages?page=${page}&page_size=${pageSize}`)
}

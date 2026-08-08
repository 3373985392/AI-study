import { afterEach, describe, expect, it, vi } from 'vitest'
import { createAdminInvite, listAdminInvites, loginAdmin } from './api'


afterEach(() => vi.unstubAllGlobals())

describe('admin api', () => {
  it('uses the isolated admin login endpoint without caching', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ authenticated: true, expiresAt: 123 }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)

    await loginAdmin('secret')

    expect(fetchMock).toHaveBeenCalledWith('/api/admin/auth/login', expect.objectContaining({
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
    }))
  })

  it('serializes filters and custom invite fields for backend models', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], page: 2, pageSize: 30, total: 0 }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ invite: { id: 'i1' }, oneTimeCode: 'CustomInvite2026_A' }), {
        status: 201, headers: { 'Content-Type': 'application/json' },
      }))
    vi.stubGlobal('fetch', fetchMock)

    await listAdminInvites({ query: '朋友', status: 'active', page: 2 })
    await createAdminInvite({
      mode: 'custom', label: '朋友', minuteLimit: 3, dayLimit: 30,
      code: 'CustomInvite2026_A', codeConfirmation: 'CustomInvite2026_A',
    })

    expect(fetchMock.mock.calls[0][0]).toContain('query=%E6%9C%8B%E5%8F%8B')
    const body = JSON.parse(fetchMock.mock.calls[1][1].body)
    expect(body).toMatchObject({ minute_limit: 3, day_limit: 30, code_confirmation: 'CustomInvite2026_A' })
  })
})

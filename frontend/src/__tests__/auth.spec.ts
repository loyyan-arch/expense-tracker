import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from '@/api/client'
import {
  authRequest,
  clearSession,
  login,
  user,
} from '@/auth'

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()

  return {
    ...actual,
    apiRequest: vi.fn(),
  }
})

const request = vi.mocked(apiRequest)

beforeEach(() => {
  request.mockReset()
  clearSession()
})

afterEach(() => {
  clearSession()
})

async function loginSuccessfully() {
  request
    .mockResolvedValueOnce({
      access_token: 'test-token',
      token_type: 'bearer',
    })
    .mockResolvedValueOnce({
      id: 1,
      username: 'learner',
    })

  await login('learner', 'example-password')
}

describe('登录状态', () => {
  it('获取用户信息失败时，不保存登录状态', async () => {
    request
      .mockResolvedValueOnce({
        access_token: 'test-token',
        token_type: 'bearer',
      })
      .mockRejectedValueOnce(new ApiError('服务异常', 503))

    await expect(login('learner', 'example-password')).rejects.toThrow(
      '服务异常',
    )

    expect(user.value).toBeNull()
  })

  it('登录后，受保护请求携带 Token', async () => {
    await loginSuccessfully()
    request.mockResolvedValueOnce([])

    await authRequest('/transactions')

    const calls = request.mock.calls
    const options = calls[calls.length - 1]?.[1]
    const headers = new Headers(options?.headers)

    expect(headers.get('Authorization')).toBe('Bearer test-token')
    expect(user.value?.username).toBe('learner')
  })

  it('受保护请求返回 401 时清除登录状态', async () => {
    await loginSuccessfully()
    request.mockRejectedValueOnce(new ApiError('Token 已失效', 401))

    await expect(authRequest('/transactions')).rejects.toMatchObject({
      status: 401,
    })

    expect(user.value).toBeNull()
  })

  it('退出后，不再发送受保护请求', async () => {
    await loginSuccessfully()
    clearSession()
    request.mockClear()

    await expect(authRequest('/transactions')).rejects.toMatchObject({
      status: 401,
    })

    expect(request).not.toHaveBeenCalled()
  })
})
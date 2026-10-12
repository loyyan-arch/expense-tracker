import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from '../client'

afterEach(() => {
  vi.unstubAllGlobals()
})

function mockResponse(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )
}

describe('apiRequest', () => {
  it('返回成功响应中的 JSON', async () => {
    mockResponse({ status: 'ok' })

    await expect(apiRequest('/health')).resolves.toEqual({
      status: 'ok',
    })
  })

  it('将 HTTP 错误转换为可展示的错误', async () => {
    mockResponse({ detail: '用户名不存在，请先注册' }, 401)

    await expect(apiRequest('/auth/login')).rejects.toMatchObject({
      status: 401,
      message: '用户名不存在，请先注册',
    })
  })

  it('204 成功响应不解析 JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    )

    await expect(
      apiRequest('/transactions/1', { method: 'DELETE' }),
    ).resolves.toBeUndefined()
  })

  it('网络失败时提供清晰提示', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )

    await expect(apiRequest('/health')).rejects.toMatchObject({
      status: 0,
      message: '无法连接服务，请检查网络或服务是否启动',
    })
  })
})
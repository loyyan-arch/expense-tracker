import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from '@/api/client'

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, apiRequest: vi.fn() }
})

const request = vi.mocked(apiRequest)
let auth: typeof import('@/auth')
const me = { id: 1, username: 'learner' }

beforeEach(async () => {
  vi.resetModules()
  request.mockReset()
  auth = await import('@/auth')
})

async function signIn() {
  request.mockResolvedValueOnce(me)
  await auth.login('learner', 'example-password')
}

describe('浏览器会话', () => {
  it('登录仅保存用户信息，不在 JS 中保存或发送 Bearer 凭证', async () => {
    await signIn()
    request.mockResolvedValueOnce([])
    await auth.authRequest('/transactions')
    expect(request).toHaveBeenNthCalledWith(1, '/auth/browser/login', expect.any(Object))
    const headers = new Headers(request.mock.calls[1]?.[1]?.headers)
    expect(headers.has('Authorization')).toBe(false)
    expect(auth.user.value).toEqual(me)
  })

  it('页面启动恢复身份，并合并同时发生的恢复请求', async () => {
    request.mockResolvedValueOnce(me)
    await Promise.all([auth.restoreSession(), auth.restoreSession()])
    expect(request).toHaveBeenCalledTimes(1)
    expect(auth.authReady.value).toBe(true)
    expect(auth.user.value).toEqual(me)
  })

  it('恢复时 401 表示未登录，不显示网络故障', async () => {
    request.mockRejectedValueOnce(new ApiError('未登录', 401))
    await auth.restoreSession()
    expect(auth.authReady.value).toBe(true)
    expect(auth.user.value).toBeNull()
    expect(auth.authRestoreError.value).toBe('')
  })

  it('网络故障不完成身份判断，重试成功后恢复', async () => {
    request.mockRejectedValueOnce(new ApiError('无法连接服务', 0))
    await expect(auth.restoreSession()).rejects.toThrow('无法连接服务')
    expect(auth.authReady.value).toBe(false)
    expect(auth.authRestoreError.value).toBe('无法连接服务')
    request.mockResolvedValueOnce(me)
    await auth.restoreSession()
    expect(auth.user.value).toEqual(me)
    expect(auth.authRestoreError.value).toBe('')
  })

  it('畸形用户响应不能被当成登录成功', async () => {
    request.mockResolvedValueOnce({ access_token: 'old-token' })
    await expect(auth.login('learner', 'password')).rejects.toThrow('获取当前用户失败')
    expect(auth.user.value).toBeNull()
  })

  it('受保护请求返回 401 时清除登录状态', async () => {
    await signIn()
    request.mockRejectedValueOnce(new ApiError('会话失效', 401))
    await expect(auth.authRequest('/transactions')).rejects.toMatchObject({ status: 401 })
    expect(auth.user.value).toBeNull()
  })

  it('退出失败保留页面状态，重试服务端退出成功才清除', async () => {
    await signIn()
    request.mockRejectedValueOnce(new ApiError('网络故障', 0))
    await expect(auth.logout()).rejects.toThrow('网络故障')
    expect(auth.user.value).toEqual(me)
    request.mockResolvedValueOnce(undefined)
    await auth.logout()
    expect(request).toHaveBeenLastCalledWith('/auth/browser/logout', { method: 'POST' })
    expect(auth.user.value).toBeNull()
    request.mockClear()
    await expect(auth.authRequest('/transactions')).rejects.toMatchObject({ status: 401 })
    expect(request).not.toHaveBeenCalled()
  })

  it('退出后才到达的恢复响应不能重新登录', async () => {
    let resolve!: (value: unknown) => void
    request.mockReturnValueOnce(new Promise((done) => { resolve = done }))
    const restoring = auth.restoreSession()
    request.mockResolvedValueOnce(undefined)
    await auth.logout()
    resolve(me)
    await restoring
    expect(auth.user.value).toBeNull()
  })

  it('旧请求的 401 不能清除新登录的用户', async () => {
    await signIn()
    let reject!: (error: unknown) => void
    request.mockReturnValueOnce(new Promise((_, fail) => { reject = fail }))
    const oldRequest = auth.authRequest('/transactions')
    await signIn()
    reject(new ApiError('旧会话失效', 401))
    await expect(oldRequest).rejects.toMatchObject({ status: 401 })
    expect(auth.user.value).toEqual(me)
  })

  it('退出后才到达的数据不能再写入页面', async () => {
    await signIn()
    let resolve!: (value: unknown) => void
    request.mockReturnValueOnce(new Promise((done) => { resolve = done }))
    const oldRequest = auth.authRequest('/transactions')
    request.mockResolvedValueOnce(undefined)
    await auth.logout()
    resolve([])
    await expect(oldRequest).rejects.toThrow('登录状态已改变')
  })
})

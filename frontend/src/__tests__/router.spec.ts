import { beforeEach, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from '@/api/client'

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, apiRequest: vi.fn() }
})

beforeEach(() => {
  vi.resetModules()
  vi.mocked(apiRequest).mockReset()
  window.history.replaceState(null, '', '/')
})

it('访问年度统计时先等待恢复，成功后保留深层页面', async () => {
  let resolve!: (value: unknown) => void
  vi.mocked(apiRequest).mockReturnValueOnce(new Promise((done) => { resolve = done }))
  const router = (await import('@/router')).default
  const navigating = router.push('/statistics/yearly')
  await vi.waitFor(() => expect(apiRequest).toHaveBeenCalledWith('/auth/me'))
  expect(router.currentRoute.value.path).not.toBe('/login')
  resolve({ id: 1, username: 'learner' })
  await navigating
  expect(router.currentRoute.value.path).toBe('/statistics/yearly')
})

it('确认没有会话后才跳转登录页', async () => {
  vi.mocked(apiRequest).mockRejectedValueOnce(new ApiError('未登录', 401))
  const router = (await import('@/router')).default
  await router.push('/transactions')
  expect(router.currentRoute.value.path).toBe('/login')
})

it('恢复遇到网络故障保留目标地址，交给 App 展示重试', async () => {
  vi.mocked(apiRequest).mockRejectedValueOnce(new ApiError('无法连接', 0))
  const router = (await import('@/router')).default
  await router.push('/statistics/yearly')
  const auth = await import('@/auth')
  expect(router.currentRoute.value.path).toBe('/statistics/yearly')
  expect(auth.authReady.value).toBe(false)
  expect(auth.authRestoreError.value).toBe('无法连接')
})

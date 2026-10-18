import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { ApiError, apiRequest } from '@/api/client'

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, apiRequest: vi.fn() }
})
vi.mock('@/views/TransactionsView.vue', () => ({ default: { template: '<p>账单页面内容</p>' } }))
vi.mock('@/views/YearlyStatisticsView.vue', () => ({ default: { template: '<p>年度页面内容</p>' } }))

let wrapper: VueWrapper | undefined
beforeEach(() => {
  vi.resetModules()
  vi.mocked(apiRequest).mockReset()
  window.history.replaceState(null, '', '/')
})
afterEach(() => wrapper?.unmount())

async function openPage() {
  const router = (await import('@/router')).default
  await router.push('/transactions')
  const App = (await import('@/App.vue')).default
  wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

it('恢复失败隐藏受保护页面，点击重试成功后展示内容', async () => {
  vi.mocked(apiRequest).mockRejectedValueOnce(new ApiError('网络故障', 0))
  const page = await openPage()
  expect(page.text()).toContain('暂时无法确认登录状态')
  expect(page.text()).not.toContain('账单页面内容')
  vi.mocked(apiRequest).mockResolvedValueOnce({ id: 1, username: 'learner' })
  await page.get('main button').trigger('click')
  await flushPromises()
  expect(page.text()).toContain('账单页面内容')
  expect(page.text()).not.toContain('暂时无法确认登录状态')
})

it('退出失败显示重试信息，成功后才离开账单页', async () => {
  vi.mocked(apiRequest).mockResolvedValueOnce({ id: 1, username: 'learner' })
  const page = await openPage()
  vi.mocked(apiRequest).mockRejectedValueOnce(new ApiError('网络故障', 0))
  await page.get('nav button').trigger('click')
  await flushPromises()
  expect(page.text()).toContain('退出未确认')
  expect(page.text()).toContain('账单页面内容')
  vi.mocked(apiRequest).mockResolvedValueOnce(undefined)
  await page.get('nav button').trigger('click')
  await flushPromises()
  expect(page.text()).not.toContain('账单页面内容')
  expect(page.text()).not.toContain('退出未确认')
})

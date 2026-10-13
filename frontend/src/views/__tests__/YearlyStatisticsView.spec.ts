import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { getYearlyStatistics } from '@/api/statistics'
import type { YearlyStatistics } from '@/api/statistics'
import YearlyStatisticsView from '../YearlyStatisticsView.vue'

vi.mock('@/api/statistics', () => ({ getYearlyStatistics: vi.fn() }))
const request = vi.mocked(getYearlyStatistics)
let wrapper: VueWrapper
function report(year: number): YearlyStatistics {
  return { year, income_cents: 0, expense_cents: 29, balance_cents: -29,
    months: Array.from({ length: 12 }, (_, i) => ({
      month: `${year}-${String(i + 1).padStart(2, '0')}`,
      income_cents: 0, expense_cents: i === 0 ? 29 : 0,
      balance_cents: i === 0 ? -29 : 0,
    })) }
}
beforeEach(() => { request.mockReset(); request.mockImplementation(async year => report(year)) })
afterEach(() => { wrapper?.unmount() })

it('renders twelve months and a negative balance', async () => {
  wrapper = mount(YearlyStatisticsView)
  await flushPromises()
  expect(wrapper.findAll('tbody tr')).toHaveLength(12)
  expect(wrapper.get('.year-totals').text()).toContain('-0.29')
})

it('rejects invalid input without requesting the backend', async () => {
  wrapper = mount(YearlyStatisticsView)
  await flushPromises()
  request.mockClear()
  await wrapper.get('input').setValue('9999')
  await wrapper.get('form').trigger('submit')
  expect(request).not.toHaveBeenCalled()
  expect(wrapper.get('[role="alert"]').text()).toContain('年份必须')
  expect(wrapper.find('table').exists()).toBe(false)
})

it('shows request errors and recovers on retry', async () => {
  request.mockRejectedValueOnce(new Error('服务暂不可用'))
  wrapper = mount(YearlyStatisticsView)
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('服务暂不可用')
  await wrapper.get('[role="alert"] button').trigger('click')
  await flushPromises()
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(wrapper.findAll('tbody tr')).toHaveLength(12)
})

it('ignores an older response after a new year was selected', async () => {
  let resolveOld!: (value: YearlyStatistics) => void
  request.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
  wrapper = mount(YearlyStatisticsView)
  await wrapper.get('input').setValue('2024')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  resolveOld(report(2023))
  await flushPromises()
  expect(wrapper.get('h2').text()).toBe('2024 年')
  expect(wrapper.get('tbody').text()).not.toContain('2023-')
})

import { beforeEach, expect, it, vi } from 'vitest'
import { authRequest } from '@/auth'
import { getYearlyStatistics } from '../statistics'

vi.mock('@/auth', () => ({ authRequest: vi.fn() }))
const request = vi.mocked(authRequest)
beforeEach(() => request.mockReset())
function emptyYear() {
  return { year: 2026, income_cents: 0, expense_cents: 0, balance_cents: 0,
    months: Array.from({ length: 12 }, (_, i) => ({
      month: `2026-${String(i + 1).padStart(2, '0')}`,
      income_cents: 0, expense_cents: 0, balance_cents: 0,
    })) }
}

it('accepts a complete empty year and calls the authenticated endpoint', async () => {
  request.mockResolvedValue(emptyYear())
  expect((await getYearlyStatistics(2026)).months).toHaveLength(12)
  expect(request).toHaveBeenCalledWith('/statistics/yearly?year=2026', { signal: undefined })
})

it.each(['missing-month', 'wrong-order', 'wrong-total', 'unsafe-amount'])('rejects malformed report: %s', async kind => {
  const data = emptyYear()
  if (kind === 'missing-month') data.months.pop()
  if (kind === 'wrong-order') data.months.reverse()
  if (kind === 'wrong-total') { data.income_cents = 10; data.balance_cents = 10 }
  if (kind === 'unsafe-amount') data.expense_cents = Number.MAX_SAFE_INTEGER + 1
  request.mockResolvedValue(data)
  await expect(getYearlyStatistics(2026)).rejects.toThrow('年度统计数据异常')
})

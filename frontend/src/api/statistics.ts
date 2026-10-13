import { authRequest } from '@/auth'

export interface Totals {
  income_cents: number
  expense_cents: number
  balance_cents: number
}

export interface YearlyStatistics extends Totals {
  year: number
  months: (Totals & { month: string })[]
}

function validTotals(value: unknown): value is Totals {
  if (!value || typeof value !== 'object') return false
  const totals = value as Totals
  return Number.isSafeInteger(totals.income_cents) && totals.income_cents >= 0
    && Number.isSafeInteger(totals.expense_cents) && totals.expense_cents >= 0
    && Number.isSafeInteger(totals.balance_cents)
    && totals.balance_cents === totals.income_cents - totals.expense_cents
}

export async function getYearlyStatistics(year: number, signal?: AbortSignal) {
  if (!Number.isInteger(year) || year < 1 || year > 9998) {
    throw new Error('年份必须是 1～9998 的整数')
  }
  const result = await authRequest<YearlyStatistics>(
    `/statistics/yearly?${new URLSearchParams({ year: String(year) })}`, { signal },
  )
  if (!result || result.year !== year || !validTotals(result)
    || !Array.isArray(result.months) || result.months.length !== 12
    || !result.months.every((month, index) => validTotals(month)
      && month.month === `${String(year).padStart(4, '0')}-${String(index + 1).padStart(2, '0')}`)
    || result.months.reduce((sum, month) => sum + month.income_cents, 0) !== result.income_cents
    || result.months.reduce((sum, month) => sum + month.expense_cents, 0) !== result.expense_cents) {
    throw new Error('年度统计数据异常，请重试')
  }
  return result
}

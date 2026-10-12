import { authRequest } from '@/auth'

export const categories = ['餐饮', '交通', '购物', '工资', '其他'] as const

export type Category = (typeof categories)[number]

export interface TransactionInput {
  kind: 'income' | 'expense'
  amount_cents: number
  category: Category
  occurred_on: string
  note: string
}

export interface Transaction extends TransactionInput {
  id: number
  created_at: string
}

interface ListOptions {
  month: string
  category: Category | ''
  offset: number
  limit: number
}

export async function listTransactions(
  options: ListOptions,
  signal?: AbortSignal,
): Promise<Transaction[]> {
  const params = new URLSearchParams({
    offset: String(options.offset),
    limit: String(options.limit),
  })

  if (options.month) params.set('month', options.month)
  if (options.category) params.set('category', options.category)

  const result = await authRequest<Transaction[]>(
    `/transactions?${params.toString()}`,
    { signal },
  )

  if (!Array.isArray(result)) {
    throw new Error('账单列表响应异常')
  }

  return result
}

export async function createTransaction(
  input: TransactionInput,
  signal?: AbortSignal,
): Promise<Transaction> {
  const result = await authRequest<Transaction>('/transactions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
    signal,
  })

  if (!result || typeof result.id !== 'number') {
    throw new Error('保存响应异常，请先查询列表确认是否已保存')
  }

  return result
}

export async function updateTransaction(
    id: number,
    input: TransactionInput,
    signal?: AbortSignal,
  ): Promise<Transaction> {
    const result = await authRequest<Transaction>(`/transactions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
      signal,
    })
  
    if (!result || typeof result.id !== 'number') {
      throw new Error('修改响应异常，请查询列表确认结果')
    }
  
    return result
  }
  
  export async function deleteTransaction(
    id: number,
    signal?: AbortSignal,
  ): Promise<void> {
    await authRequest<void>(`/transactions/${id}`, {
      method: 'DELETE',
      signal,
    })
  }
  
  export interface MonthlyStatistics {
    month: string
    income_cents: number
    expense_cents: number
    balance_cents: number
  }
  
  export async function getMonthlyStatistics(
    month: string,
    signal?: AbortSignal,
  ): Promise<MonthlyStatistics> {
    const params = new URLSearchParams({ month })
  
    const result = await authRequest<MonthlyStatistics>(
      `/statistics/monthly?${params.toString()}`,
      { signal },
    )
  
    if (
      !result ||
      result.month !== month ||
      !Number.isSafeInteger(result.income_cents) ||
      !Number.isSafeInteger(result.expense_cents) ||
      !Number.isSafeInteger(result.balance_cents) ||
      result.income_cents < 0 ||
      result.expense_cents < 0
    ) {
      throw new Error('月度统计数据异常')
    }
  
    return result
  }
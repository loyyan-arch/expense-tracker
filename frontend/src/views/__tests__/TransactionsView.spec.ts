import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import TransactionsView from '../TransactionsView.vue'
import {
  createTransaction,
  deleteTransaction,
  getMonthlyStatistics,
  listTransactions,
  updateTransaction,
} from '@/api/transactions'
import type { Transaction } from '@/api/transactions'

vi.mock('@/api/transactions', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@/api/transactions')>()

  return {
    ...actual,
    createTransaction: vi.fn(),
    deleteTransaction: vi.fn(),
    getMonthlyStatistics: vi.fn(),
    listTransactions: vi.fn(),
    updateTransaction: vi.fn(),
  }
})

const bill: Transaction = {
  id: 7,
  kind: 'expense',
  amount_cents: 2550,
  category: '餐饮',
  occurred_on: '2026-10-12',
  note: '午餐',
  created_at: '2026-10-12T12:00:00',
}

let wrapper: VueWrapper

function button(text: string) {
  const result = wrapper.findAll('button').find(
    (item) => item.text() === text,
  )

  if (!result) throw new Error(`找不到按钮：${text}`)

  return result
}

beforeEach(async () => {
  vi.resetAllMocks()

  vi.mocked(listTransactions).mockResolvedValue([{ ...bill }])

  vi.mocked(getMonthlyStatistics).mockImplementation(async (month) => ({
    month,
    income_cents: 0,
    expense_cents: 2550,
    balance_cents: -2550,
  }))

  vi.mocked(createTransaction).mockResolvedValue({ ...bill })
  vi.mocked(updateTransaction).mockResolvedValue({
    ...bill,
    amount_cents: 3000,
  })
  vi.mocked(deleteTransaction).mockResolvedValue(undefined)

  wrapper = mount(TransactionsView)
  await flushPromises()
})

afterEach(() => {
  wrapper?.unmount()
  vi.restoreAllMocks()
})

describe('账单页面', () => {
  it('取消编辑时不保存，原账单保持不变', async () => {
    await button('修改').trigger('click')

    await wrapper.get('input[inputmode="decimal"]').setValue('30.00')
    await button('取消修改').trigger('click')

    expect(updateTransaction).not.toHaveBeenCalled()
    expect(createTransaction).not.toHaveBeenCalled()
    expect(wrapper.get('tbody').text()).toContain('25.50')
    expect(wrapper.get('h2').text()).toBe('记一笔')
  })

  it('保存编辑时按分提交，并刷新列表和统计', async () => {
    await button('修改').trigger('click')
    await wrapper.get('input[inputmode="decimal"]').setValue('30.00')

    vi.mocked(listTransactions).mockResolvedValue([
      { ...bill, amount_cents: 3000 },
    ])
    vi.mocked(getMonthlyStatistics).mockResolvedValue({
      month: '2026-10',
      income_cents: 0,
      expense_cents: 3000,
      balance_cents: -3000,
    })

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(updateTransaction).toHaveBeenCalledWith(
      7,
      expect.objectContaining({ amount_cents: 3000 }),
      expect.any(AbortSignal),
    )
    expect(createTransaction).not.toHaveBeenCalled()
    expect(wrapper.get('tbody').text()).toContain('30.00')
    expect(wrapper.get('.statistics').text()).toContain('-30.00')
    expect(wrapper.text()).toContain('修改成功')
  })

  it('取消删除时不调用删除接口', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    await button('删除').trigger('click')

    expect(deleteTransaction).not.toHaveBeenCalled()
    expect(wrapper.get('tbody').text()).toContain('午餐')
  })

  it('确认删除后重新查询列表和统计', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    vi.mocked(listTransactions).mockResolvedValue([])
    vi.mocked(getMonthlyStatistics).mockImplementation(async (month) => ({
      month,
      income_cents: 0,
      expense_cents: 0,
      balance_cents: 0,
    }))

    await button('删除').trigger('click')
    await flushPromises()

    expect(deleteTransaction).toHaveBeenCalledWith(
      7,
      expect.any(AbortSignal),
    )
    expect(listTransactions).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 0 }),
      expect.any(AbortSignal),
    )
    expect(wrapper.text()).toContain('删除成功')
    expect(wrapper.text()).toContain('当前条件下没有账单')
    expect(wrapper.get('.statistics').text()).not.toContain('-25.50')
    expect(getMonthlyStatistics).toHaveBeenCalledTimes(2)
  })

  it('统计请求失败时仍显示账单列表', async () => {
    vi.mocked(getMonthlyStatistics).mockRejectedValue(
      new Error('统计服务暂时不可用'),
    )

    await button('刷新列表和统计').trigger('click')
    await flushPromises()

    expect(wrapper.get('tbody').text()).toContain('午餐')
    expect(wrapper.text()).toContain('统计服务暂时不可用')
    expect(button('重试统计').exists()).toBe(true)
  })

  it('保存成功但列表刷新失败时，保留保存成功提示', async () => {
    await wrapper.get('input[inputmode="decimal"]').setValue('25.50')

    vi.mocked(listTransactions).mockRejectedValue(
      new Error('查询暂时失败'),
    )

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(createTransaction).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('新增成功')
    expect(wrapper.text()).toContain('列表加载失败')
    expect(wrapper.text()).toContain('查询暂时失败')
  })
})
import { describe, expect, it } from 'vitest'
import { centsToYuan, yuanToCents } from '../money'

describe('元转分', () => {
  it.each([
    ['25', 2500],
    ['25.5', 2550],
    ['25.50', 2550],
    ['0.01', 1],
    ['0.29', 29],
    ['1.10', 110],
  ])('%s 元转换为 %i 分', (input, expected) => {
    expect(yuanToCents(input)).toBe(expected)
  })

  it.each([
    '',
    '0',
    '-1',
    '1.001',
    'abc',
    '1e3',
    '999999999999999999',
  ])('拒绝不合法金额：%s', (input) => {
    expect(() => yuanToCents(input)).toThrow()
  })
})

describe('分转元', () => {
  it.each([
    [1, '0.01'],
    [29, '0.29'],
    [2550, '25.50'],
    [0, '0.00'],
    [-1, '-0.01'],
    [-2550, '-25.50'],
  ])('%i 分显示为 %s 元', (input, expected) => {
    expect(centsToYuan(input)).toBe(expected)
  })
})
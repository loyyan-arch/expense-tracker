export function yuanToCents(input: string): number {
    const value = input.trim()
  
    if (!/^\d+(\.\d{1,2})?$/.test(value)) {
      throw new Error('金额必须是正数，最多保留两位小数')
    }
  
    const [yuan = '', decimal = ''] = value.split('.')
    const cents = Number(yuan) * 100 + Number(decimal.padEnd(2, '0'))
  
    if (!Number.isSafeInteger(cents) || cents <= 0) {
      throw new Error('金额必须大于 0，且不能超过可精确处理的范围')
    }
  
    return cents
  }
  
  export function centsToYuan(cents: number): string {
    if (!Number.isSafeInteger(cents)) {
      throw new Error('金额数据异常')
    }
  
    const sign = cents < 0 ? '-' : ''
    const digits = String(Math.abs(cents)).padStart(3, '0')
  
    return `${sign}${digits.slice(0, -2)}.${digits.slice(-2)}`
  }
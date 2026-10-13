<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { getYearlyStatistics } from '@/api/statistics'
import type { YearlyStatistics } from '@/api/statistics'
import { centsToYuan } from '@/utils/money'

const year = ref(String(new Date().getFullYear()))
const report = ref<YearlyStatistics | null>(null)
const loading = ref(false)
const error = ref('')
let controller: AbortController | undefined
let version = 0

async function loadReport() {
  controller?.abort()
  const current = ++version
  report.value = null
  error.value = ''
  loading.value = false
  const selected = Number(year.value)
  if (!/^\d{1,4}$/.test(year.value) || selected < 1 || selected > 9998) {
    error.value = '年份必须是 1～9998 的整数'
    return
  }
  const request = new AbortController()
  controller = request
  loading.value = true
  try {
    const result = await getYearlyStatistics(selected, request.signal)
    if (current === version) report.value = result
  } catch (cause) {
    if (current === version) {
      error.value = cause instanceof Error ? cause.message : '年度统计加载失败'
    }
  } finally {
    if (current === version) loading.value = false
  }
}

onMounted(loadReport)
onBeforeUnmount(() => { version += 1; controller?.abort() })
</script>

<template>
  <section class="yearly-page">
    <h1>年度收支总览</h1>
    <p>按账单发生日期计算，包含你的全年所有分类，不受账单列表分页影响。</p>
    <form @submit.prevent="loadReport">
      <label for="report-year">年份</label>
      <input id="report-year" v-model="year" type="text" inputmode="numeric"
        maxlength="4" required aria-describedby="year-help" />
      <small id="year-help">输入 1～9998，例如 2026</small>
      <button type="submit">{{ loading ? '重新查询' : '查询年度' }}</button>
    </form>
    <p v-if="loading" role="status">正在加载年度统计…</p>
    <div v-else-if="error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="loadReport">重试</button>
    </div>
    <template v-else-if="report">
      <h2>{{ report.year }} 年</h2>
      <dl class="year-totals">
        <div><dt>全年收入</dt><dd>{{ centsToYuan(report.income_cents) }} 元</dd></div>
        <div><dt>全年支出</dt><dd>{{ centsToYuan(report.expense_cents) }} 元</dd></div>
        <div><dt>全年结余</dt><dd>{{ centsToYuan(report.balance_cents) }} 元</dd></div>
      </dl>
      <p v-if="report.income_cents === 0 && report.expense_cents === 0">这一年还没有账单。</p>
      <div class="year-table" role="region" aria-label="年度每月收支明细，可横向滚动" tabindex="0">
        <table>
          <caption>{{ report.year }} 年每月明细（元）</caption>
          <thead><tr><th scope="col">月份</th><th scope="col">收入</th><th scope="col">支出</th><th scope="col">结余</th></tr></thead>
          <tbody><tr v-for="month in report.months" :key="month.month">
            <th scope="row">{{ month.month }}</th>
            <td>{{ centsToYuan(month.income_cents) }}</td>
            <td>{{ centsToYuan(month.expense_cents) }}</td>
            <td>{{ centsToYuan(month.balance_cents) }}</td>
          </tr></tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.yearly-page { padding: 24px; border: var(--line); border-radius: 18px; background: var(--paper); }
form { display: grid; gap: 8px; max-width: 300px; }
.year-totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
.year-totals div { padding: 16px; border: var(--line); border-radius: 12px; background: var(--green); }
dd { margin: 8px 0 0; font-size: 1.3rem; font-weight: 700; overflow-wrap: anywhere; }
.year-table { overflow-x: auto; }
table { width: 100%; min-width: 440px; border-collapse: collapse; }
caption { text-align: left; padding: 12px 0; }
th, td { padding: 12px; text-align: right; border-bottom: 1px solid var(--muted); }
th:first-child { text-align: left; }
@media (max-width: 600px) { .yearly-page { padding: 16px; } }
</style>

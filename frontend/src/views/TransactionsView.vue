<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  categories,
  createTransaction,
  deleteTransaction,
  getMonthlyStatistics,
  listTransactions,
  updateTransaction,
} from '@/api/transactions'
import type {
  Category,
  MonthlyStatistics,
  Transaction,
  TransactionInput,
} from '@/api/transactions'
import { centsToYuan, yuanToCents } from '@/utils/money'

function localToday(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function defaultForm() {
  return {
    kind: 'expense' as TransactionInput['kind'],
    amount: '',
    category: '餐饮' as Category,
    occurred_on: localToday(),
    note: '',
  }
}

const form = reactive(defaultForm())
const editingId = ref<number | null>(null)

const month = ref(localToday().slice(0, 7))
const category = ref<Category | ''>('')
const offset = ref(0)
const pageSize = 10

const bills = ref<Transaction[]>([])
const hasNext = ref(false)
const loading = ref(false)
const saving = ref(false)
const listError = ref('')
const saveError = ref('')
const saveMessage = ref('')

const statistics = ref<MonthlyStatistics | null>(null)
const statisticsLoading = ref(false)
const statisticsError = ref('')

const busy = computed(
  () => loading.value || saving.value || statisticsLoading.value,
)

let listController: AbortController | undefined
let statisticsController: AbortController | undefined
let saveController: AbortController | undefined
let listVersion = 0
let statisticsVersion = 0
let disposed = false

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

function resetForm() {
  editingId.value = null
  Object.assign(form, defaultForm())
}

function startEdit(bill: Transaction) {
  if (busy.value || editingId.value !== null) return

  editingId.value = bill.id
  Object.assign(form, {
    kind: bill.kind,
    amount: centsToYuan(bill.amount_cents),
    category: bill.category,
    occurred_on: bill.occurred_on,
    note: bill.note,
  })

  saveError.value = ''
  saveMessage.value = ''
}

function cancelEdit() {
  if (busy.value) return

  resetForm()
  saveError.value = ''
  saveMessage.value = ''
}

async function loadBills() {
  listController?.abort()
  const controller = new AbortController()
  listController = controller
  const version = ++listVersion

  loading.value = true
  listError.value = ''
  bills.value = []
  hasNext.value = false

  try {
    const result = await listTransactions(
      {
        month: month.value,
        category: category.value,
        offset: offset.value,
        limit: pageSize + 1,
      },
      controller.signal,
    )

    if (disposed || version !== listVersion) return

    bills.value = result.slice(0, pageSize)
    hasNext.value = result.length > pageSize
  } catch (error) {
    if (disposed || version !== listVersion) return

    listError.value = errorText(error)
  } finally {
    if (!disposed && version === listVersion) {
      loading.value = false
    }
  }
}

async function loadStatistics() {
  statisticsController?.abort()
  const version = ++statisticsVersion
  const selectedMonth = month.value

  statistics.value = null
  statisticsError.value = ''
  statisticsLoading.value = false

  // 全部月份视图没有对应的单月统计。
  if (!selectedMonth) return

  const controller = new AbortController()
  statisticsController = controller
  statisticsLoading.value = true

  try {
    const result = await getMonthlyStatistics(
      selectedMonth,
      controller.signal,
    )

    if (disposed || version !== statisticsVersion) return

    statistics.value = result
  } catch (error) {
    if (disposed || version !== statisticsVersion) return

    statisticsError.value = errorText(error)
  } finally {
    if (!disposed && version === statisticsVersion) {
      statisticsLoading.value = false
    }
  }
}

async function refreshAll() {
  // 两个函数各自处理错误，一项失败不会隐藏另一项的结果。
  await Promise.all([loadBills(), loadStatistics()])
}

function applyFilters() {
  offset.value = 0
  void refreshAll()
}

function changePage(direction: -1 | 1) {
  if (busy.value || editingId.value !== null || listError.value) return
  if (direction === -1 && offset.value === 0) return
  if (direction === 1 && !hasNext.value) return

  offset.value += direction * pageSize
  void loadBills()
}

async function saveBill() {
  if (busy.value) return

  saving.value = true
  saveError.value = ''
  saveMessage.value = ''

  const controller = new AbortController()
  saveController = controller
  const id = editingId.value

  try {
    const input: TransactionInput = {
      kind: form.kind,
      amount_cents: yuanToCents(form.amount),
      category: form.category,
      occurred_on: form.occurred_on,
      note: form.note,
    }

    const saved = id === null
      ? await createTransaction(input, controller.signal)
      : await updateTransaction(id, input, controller.signal)

    if (disposed) return

    resetForm()
    saveMessage.value = id === null
      ? '新增成功，已切换到该账单所在月份'
      : '修改成功，已切换到该账单所在月份'

    month.value = saved.occurred_on.slice(0, 7)
    category.value = ''
    offset.value = 0

    await refreshAll()
  } catch (error) {
    if (!disposed) {
      saveError.value = errorText(error)
    }
  } finally {
    if (!disposed) {
      saving.value = false
    }
  }
}

async function removeBill(bill: Transaction) {
  if (busy.value || editingId.value !== null) return

  const confirmed = window.confirm(
    `确定删除 ${bill.occurred_on} 的${bill.category}账单`
    + `（${centsToYuan(bill.amount_cents)} 元）吗？此操作无法撤销。`,
  )

  if (!confirmed) return

  saving.value = true
  saveError.value = ''
  saveMessage.value = ''

  const controller = new AbortController()
  saveController = controller

  try {
    await deleteTransaction(bill.id, controller.signal)

    if (disposed) return

    saveMessage.value = '删除成功，已返回第一页'
    offset.value = 0

    await refreshAll()
  } catch (error) {
    if (!disposed) {
      saveError.value = errorText(error)
    }
  } finally {
    if (!disposed) {
      saving.value = false
    }
  }
}

onMounted(() => {
  void refreshAll()
})

onBeforeUnmount(() => {
  disposed = true
  listVersion += 1
  statisticsVersion += 1
  listController?.abort()
  statisticsController?.abort()
  saveController?.abort()
})
</script>

<template>
  <section>
    <h2>
      {{ editingId === null ? '记一笔' : '修改账单' }}
    </h2>

    <p v-if="editingId !== null">
      正在编辑账单 #{{ editingId }}，保存后生效。
    </p>

    <form @submit.prevent="saveBill">
      <fieldset :disabled="busy">
        <legend>账单信息</legend>

        <label>
          收支类型
          <select v-model="form.kind">
            <option value="expense">支出</option>
            <option value="income">收入</option>
          </select>
        </label>

        <label>
          金额（元）
          <input
            v-model="form.amount"
            type="text"
            inputmode="decimal"
            placeholder="例如 25.50"
            required
          />
        </label>

        <label>
          分类
          <select v-model="form.category">
            <option v-for="item in categories" :key="item" :value="item">
              {{ item }}
            </option>
          </select>
        </label>

        <label>
          日期
          <input
            v-model="form.occurred_on"
            type="date"
            min="0001-01-01"
            max="9998-12-31"
            required
          />
        </label>

        <label>
          备注
          <input v-model="form.note" maxlength="200" />
        </label>

        <button type="submit">
          {{ saving
            ? '处理中…'
            : editingId === null ? '保存账单' : '保存修改'
          }}
        </button>

        <button
          v-if="editingId !== null"
          type="button"
          @click="cancelEdit"
        >
          取消修改
        </button>
      </fieldset>
    </form>

    <p v-if="saveError" role="alert" class="error">
      {{ saveError }}
    </p>
    <p role="status">{{ saveMessage }}</p>
  </section>

  <section>
    <h2>月度收支统计</h2>

    <p v-if="!month">请选择一个月份查看统计。</p>

    <template v-else>
      <p>{{ month }} 全月统计，包含全部分类和全部分页。</p>

      <p v-if="statisticsLoading" role="status">
        统计加载中…
      </p>

      <p v-else-if="statisticsError" role="alert" class="error">
        {{ statisticsError }}
      </p>

      <dl v-else-if="statistics" class="statistics">
        <div>
          <dt>收入</dt>
          <dd>{{ centsToYuan(statistics.income_cents) }} 元</dd>
        </div>
        <div>
          <dt>支出</dt>
          <dd>{{ centsToYuan(statistics.expense_cents) }} 元</dd>
        </div>
        <div>
          <dt>结余</dt>
          <dd>{{ centsToYuan(statistics.balance_cents) }} 元</dd>
        </div>
      </dl>

      <button
        v-if="statisticsError"
        type="button"
        :disabled="busy"
        @click="loadStatistics"
      >
        重试统计
      </button>
    </template>
  </section>

  <section>
    <h2>我的账单</h2>

    <fieldset :disabled="busy || editingId !== null">
      <legend>筛选条件</legend>

      <label>
        月份（清空可查看全部月份）
        <input
          v-model="month"
          type="month"
          min="0001-01"
          max="9998-12"
          @change="applyFilters"
        />
      </label>

      <label>
        分类
        <select v-model="category" @change="applyFilters">
          <option value="">全部分类</option>
          <option v-for="item in categories" :key="item" :value="item">
            {{ item }}
          </option>
        </select>
      </label>

      <button type="button" @click="refreshAll">
        刷新列表和统计
      </button>
    </fieldset>

    <p role="status">{{ loading ? '加载中…' : '' }}</p>

    <p v-if="listError" role="alert" class="error">
      列表加载失败：{{ listError }}。请点击“刷新列表和统计”重试。
    </p>

    <template v-if="!loading && !listError">
      <p v-if="bills.length === 0">当前条件下没有账单。</p>

      <div
        v-else
        class="table-wrapper"
        role="region"
        aria-label="账单列表，可横向滚动"
        tabindex="0"
      >
        <table>
          <thead>
            <tr>
              <th scope="col">日期</th>
              <th scope="col">收支</th>
              <th scope="col">分类</th>
              <th scope="col">金额（元）</th>
              <th scope="col">备注</th>
              <th scope="col">操作</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="bill in bills" :key="bill.id">
              <td>{{ bill.occurred_on }}</td>
              <td>{{ bill.kind === 'income' ? '收入' : '支出' }}</td>
              <td>{{ bill.category }}</td>
              <td>
                {{ bill.kind === 'income' ? '+' : '-' }}
                {{ centsToYuan(bill.amount_cents) }}
              </td>
              <td>{{ bill.note || '—' }}</td>
              <td>
                <div class="row-actions">
                  <button
                    type="button"
                    :disabled="busy || editingId !== null"
                    @click="startEdit(bill)"
                  >
                    修改
                  </button>

                  <button
                    type="button"
                    :disabled="busy || editingId !== null"
                    @click="removeBill(bill)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div class="pagination">
      <button
        type="button"
        :disabled="busy || editingId !== null || !!listError || offset === 0"
        @click="changePage(-1)"
      >
        上一页
      </button>

      <span>第 {{ offset / pageSize + 1 }} 页</span>

      <button
        type="button"
        :disabled="busy || editingId !== null || !!listError || !hasNext"
        @click="changePage(1)"
      >
        下一页
      </button>
    </div>
  </section>
</template>

<style scoped>
section + section {
  margin-top: 24px;
}

fieldset {
  display: grid;
  gap: 12px;
  min-width: 0;
  margin: 0;
  padding: 16px;
  border: 1px solid #d6dde3;
  border-radius: 8px;
}

label {
  display: grid;
  gap: 6px;
}

input,
select,
button {
  min-width: 0;
  padding: 10px;
  font: inherit;
}

button {
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
}

.error {
  color: #b42318;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e2e8ee;
}

td:nth-child(5) {
  overflow-wrap: anywhere;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}

.statistics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.statistics div {
  padding: 16px;
  background: #f4f6f8;
  border-radius: 8px;
}

.statistics dt {
  color: #52616b;
}

.statistics dd {
  margin: 8px 0 0;
  font-size: 1.25rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.row-actions {
  display: flex;
  gap: 8px;
}

table {
  min-width: 620px;
}

.pagination {
  flex-wrap: wrap;
}

</style>
import { readonly, ref } from 'vue'
import { ApiError, apiRequest } from '@/api/client'

interface User {
  id: number
  username: string
}

const currentUser = ref<User | null>(null)
const notice = ref('')
const ready = ref(false)
const restoreError = ref('')
let revision = 0
let restoring: Promise<void> | undefined

export const user = readonly(currentUser)
export const authNotice = readonly(notice)
export const authReady = readonly(ready)
export const authRestoreError = readonly(restoreError)

export function clearSession(message = '') {
  revision += 1
  currentUser.value = null
  notice.value = message
  ready.value = true
  restoreError.value = ''
}

function requireUser(value: User | undefined): User {
  if (!value || !Number.isSafeInteger(value.id) || value.id <= 0 ||
      typeof value.username !== 'string' || !value.username) {
    throw new Error('获取当前用户失败，请重试')
  }
  return value
}

// 同时发生的路由导航共用一次恢复请求。网络错误可以再次调用重试。
export function restoreSession(): Promise<void> {
  if (ready.value) return Promise.resolve()
  if (restoring) return restoring
  const started = revision
  restoreError.value = ''
  const pending = (async () => {
    try {
      const me = requireUser(await apiRequest<User>('/auth/me'))
      if (revision !== started) return
      currentUser.value = me
      ready.value = true
    } catch (error) {
      if (revision !== started) return
      if (error instanceof ApiError && error.status === 401) {
        clearSession()
        return
      }
      restoreError.value = authErrorMessage(error)
      throw error
    }
  })()
  restoring = pending
  void pending.finally(() => {
    if (restoring === pending) restoring = undefined
  }).catch(() => {})
  return pending
}

export async function register(
  username: string,
  password: string,
  signal?: AbortSignal,
) {
  const result = await apiRequest<User>('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
    signal,
  })

  if (!result || typeof result.id !== 'number') {
    throw new Error('注册响应异常，请尝试登录确认账号是否创建成功')
  }

  return result
}

export async function login(
  username: string,
  password: string,
  signal?: AbortSignal,
) {
  const started = ++revision
  const result = await apiRequest<User>('/auth/browser/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
    signal,
  })

  const me = requireUser(result)

  // 离开登录页面后，不再写入此次请求的结果。
  if (signal?.aborted || revision !== started) {
    throw new Error('登录已取消')
  }

  currentUser.value = me
  notice.value = ''
  ready.value = true
  restoreError.value = ''
}

export async function logout() {
  const started = ++revision
  await apiRequest('/auth/browser/logout', { method: 'POST' })
  if (revision !== started) throw new Error('登录状态已改变，请重新操作')
  clearSession()
}

// 后续账单和统计接口统一使用这个函数。
export async function authRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T | undefined> {
  const started = revision

  if (!currentUser.value) {
    clearSession('请先登录')
    throw new ApiError('请先登录', 401)
  }

  try {
    const result = await apiRequest<T>(path, options)

    if (revision !== started) {
      throw new Error('登录状态已改变，请重新操作')
    }

    return result
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      revision === started
    ) {
      clearSession('登录已失效，请重新登录')
    }

    throw error
  }
}

export function authErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) {
    const seconds = Number(error.retryAfter)

    return Number.isFinite(seconds) && seconds > 0
      ? `登录请求过于频繁，请在 ${Math.ceil(seconds)} 秒后重试`
      : error.message
  }

  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

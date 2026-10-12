import { readonly, ref } from 'vue'
import { ApiError, apiRequest } from '@/api/client'

interface User {
  id: number
  username: string
}

interface TokenResponse {
  access_token: string
  token_type: string
}

const currentUser = ref<User | null>(null)
const notice = ref('')
let accessToken = ''

export const user = readonly(currentUser)
export const authNotice = readonly(notice)

export function clearSession(message = '') {
  accessToken = ''
  currentUser.value = null
  notice.value = message
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
  const result = await apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
    signal,
  })

  if (
    !result ||
    typeof result.access_token !== 'string' ||
    !result.access_token ||
    result.token_type !== 'bearer'
  ) {
    throw new Error('登录响应异常，请重试')
  }

  // 获取真实用户信息，两次请求都成功后才保存登录状态。
  const me = await apiRequest<User>('/auth/me', {
    headers: { Authorization: `Bearer ${result.access_token}` },
    signal,
  })

  if (
    !me ||
    typeof me.id !== 'number' ||
    typeof me.username !== 'string'
  ) {
    throw new Error('获取当前用户失败，请重新登录')
  }

  // 离开登录页面后，不再写入此次请求的结果。
  if (signal?.aborted) {
    throw new Error('登录已取消')
  }

  accessToken = result.access_token
  currentUser.value = me
  notice.value = ''
}

// 后续账单和统计接口统一使用这个函数。
export async function authRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T | undefined> {
  const requestToken = accessToken

  if (!requestToken) {
    clearSession('请先登录')
    throw new ApiError('请先登录', 401)
  }

  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${requestToken}`)

  try {
    const result = await apiRequest<T>(path, { ...options, headers })

    if (accessToken !== requestToken) {
      throw new Error('登录状态已改变，请重新操作')
    }

    return result
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      accessToken === requestToken
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
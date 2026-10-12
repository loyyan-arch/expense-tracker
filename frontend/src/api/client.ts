export class ApiError extends Error {
    status: number
    retryAfter: string | null
  
    constructor(
      message: string,
      status: number,
      retryAfter: string | null = null,
    ) {
      super(message)
      this.name = 'ApiError'
      this.status = status
      this.retryAfter = retryAfter
    }
  }
  
  function getErrorMessage(data: unknown, status: number): string {
    if (typeof data === 'object' && data !== null && 'detail' in data) {
      const detail = data.detail
  
      if (typeof detail === 'string') {
        return detail
      }
  
      // 后端参数校验失败时，detail 是一个数组。
      if (Array.isArray(detail)) {
        return '提交的数据不符合要求，请检查后重试'
      }
    }
  
    return `请求失败（HTTP ${status}）`
  }
  
  export async function apiRequest<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T | undefined> {
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
  
    let response: Response
  
    try {
      response = await fetch(`/api${path}`, {
        ...options,
        headers,
      })
    } catch {
      throw new ApiError('无法连接服务，请检查网络或服务是否启动', 0)
    }
  
    // 删除接口成功时返回 204，没有 JSON 响应体。
    if (response.status === 204) {
      return undefined
    }
  
    let data: unknown
  
    try {
      data = await response.json()
    } catch {
      if (!response.ok) {
        throw new ApiError(
          `请求失败（HTTP ${response.status}），服务未返回有效 JSON`,
          response.status,
          response.headers.get('Retry-After'),
        )
      }
  
      throw new ApiError('服务返回的数据格式异常', response.status)
    }
  
    if (!response.ok) {
      throw new ApiError(
        getErrorMessage(data, response.status),
        response.status,
        response.headers.get('Retry-After'),
      )
    }
  
    return data as T
  }
import axios, { type AxiosRequestConfig, type AxiosError, type AxiosResponse } from 'axios'
import { toast } from '@/utils/toast'
import router from '@/router'

const TOKEN_KEY = 'access_token'
const MAX_TIMEOUT = 10000
const BASE_URL = '/api/v1'
const URLS = {
  LOGIN: '/auth/login',
  REFRESH: '/auth/refresh'
}

interface CustomRequestConfig extends AxiosRequestConfig {
  _retry?: boolean
}

interface PendingRequest {
  resolve: (token: string) => void
  reject: (reason: unknown) => void
}

interface ApiErrorResponse {
  detail?: string | Array<{
    msg: string;
    type?: string;
    loc?: (string | number)[];
  }>
}

const http = axios.create({
  baseURL: BASE_URL,
  timeout: MAX_TIMEOUT
})

const refreshHttp = axios.create({
  baseURL: BASE_URL,
  timeout: MAX_TIMEOUT
})

let isRefreshing = false
let failedQueue: PendingRequest[] = []
let isLoggingOut = false

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      if (!isLoggingOut) {
        prom.reject(error)
      }
    } else {
      prom.resolve(token as string)
    }
  })
  failedQueue = []
}

const getErrorMessage = (errorData: ApiErrorResponse): string => {
  if (!errorData?.detail) return '网络请求失败'

  if (typeof errorData.detail === 'string') {
    return errorData.detail
  }

  if (Array.isArray(errorData.detail)) {
    for (const err of errorData.detail) {
      if (err.loc && err.loc.includes('email')) {
        return '请输入有效的电子邮箱地址'
      }
      if (err.msg) return err.msg
    }
    return '请求参数错误'
  }

  return '未知错误'
}

const handleLogout = () => {
  if (isLoggingOut) return
  isLoggingOut = true

  localStorage.removeItem(TOKEN_KEY)

  const currentPath = router.currentRoute.value.fullPath

  if (currentPath !== '/login') {
    toast.error('登录已过期，请重新登录')
    router.push({
      path: '/login',
      query: { redirect: currentPath }
    })
  }

  setTimeout(() => { isLoggingOut = false }, 3000)
}

/**
 * Request Interceptor
 * Automatically attaches the Access Token to headers if available.
 */
http.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/**
 * Response Interceptor
 * Handles global error scenarios, specifically 401 Unauthorized and Pydantic validation errors.
 */
http.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as CustomRequestConfig

    if (isLoggingOut) {
      return new Promise(() => {})
    }

    if (!error.response) {
      toast.error('网络连接异常')
      return Promise.reject(error)
    }

    const errorData = error.response.data as ApiErrorResponse
    const status = error.response.status
    const requestUrl = originalRequest.url || ''

    // Handle 401 Unauthorized
    if (status === 401) {
      // Case 1: Login failure (Invalid credentials)
      if (requestUrl.includes(URLS.LOGIN)) {
        const msg = typeof errorData.detail === 'string'
          ? errorData.detail
          : '用户名或密码错误'
        toast.error(msg)
        return Promise.reject(error)
      }
      // Case 2: Refresh Token expired or invalid
      if (requestUrl.includes(URLS.REFRESH)) {
        handleLogout()
        return new Promise(() => {})
      }
      // Case 3: Normal 401, try to refresh
      if (!originalRequest._retry) {
        if (isRefreshing) {
          return new Promise<AxiosResponse>((resolve, reject) => {
            failedQueue.push({ resolve: (token) => {
              if (originalRequest.headers) {
                originalRequest.headers['Authorization'] = 'Bearer ' + token
              }
              resolve(http(originalRequest))
            }, reject })
          })
        }

        originalRequest._retry = true
        isRefreshing = true

        try {
          const { data } = await refreshHttp.post(URLS.REFRESH)

          const newToken = data.access_token

          localStorage.setItem(TOKEN_KEY, newToken)

          if (originalRequest.headers) {
            originalRequest.headers['Authorization'] = `Bearer ${newToken}`
          }

          processQueue(null, newToken)

          return http(originalRequest)

        } catch (refreshError) {
          processQueue(refreshError, null)
          handleLogout()
          return new Promise(() => {})
        } finally {
          isRefreshing = false
        }
      }
      else {
        handleLogout()
        return new Promise(() => {})
      }
    }

    // Handle other errors (400, 422, 500, etc.)
    const displayMsg = getErrorMessage(errorData)
    if (status !== 401) {
        toast.error(displayMsg)
    }
    return Promise.reject(error)
  }
)

export default http

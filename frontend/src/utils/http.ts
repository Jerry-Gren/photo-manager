import axios from 'axios'
import { toast } from '@/utils/toast'
import router from '@/router'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 10000
})

/**
 * Request Interceptor
 * Automatically attaches the Access Token to headers if available.
 */
http.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
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
  error => {
    const requestUrl = error.config?.url || ''

    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      // Case 1: Login failure (Invalid credentials)
      if (requestUrl.includes('/auth/login')) {
        const msg = error.response.data?.detail || '用户名或密码错误'
        toast.error(msg)
      }
      // Case 2: Token expired or invalid
      else {
        if (localStorage.getItem('access_token')) {
            toast.error('登录已过期，请重新登录')
        }
        localStorage.removeItem('access_token')
        router.push('/login')
      }
    } else {
      // Handle other errors (400, 422, 500, etc.)
      let msg = error.response?.data?.detail || '网络请求失败'

      // Format Pydantic validation errors (returned as array)
      if (Array.isArray(msg)) {
        const rawMsg = msg[0].msg || '请求参数错误'
        // Translate common technical error messages to user-friendly text
        if (rawMsg.includes('value is not a valid email address')) {
          msg = '请输入有效的电子邮箱地址'
        } else {
          msg = rawMsg;
        }
      }
      toast.error(msg)
    }

    return Promise.reject(error)
  }
)

export default http

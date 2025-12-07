import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '@/utils/http'

interface UserProfile {
  id: number
  username: string
  email: string
  role: string
  created_at: string
}

interface LoginForm {
  username: string
  password: string
}

interface RegisterForm {
  username: string
  email: string
  password: string
}

interface AuthResponse {
  access_token: string
  token_type: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('access_token') || '')
  const user = ref<UserProfile | null>(null)

  async function login(form: LoginForm) {
    const formData = new FormData()
    formData.append('username', form.username)
    formData.append('password', form.password)

    const res = await http.post<AuthResponse>('/auth/login', formData)
    token.value = res.data.access_token
    localStorage.setItem('access_token', token.value)

    await fetchProfile()
  }

  async function register(form: RegisterForm) {
    await http.post('/auth/register', {
      username: form.username,
      email: form.email,
      password: form.password
    })
  }

  async function fetchProfile() {
    if (!token.value) return
    const res = await http.get<UserProfile>('/auth/me')
    user.value = res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    http.post('/auth/logout')
  }

  return { token, user, login, register, fetchProfile, logout }
})

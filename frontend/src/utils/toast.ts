import { reactive } from 'vue'

export type ToastType = 'success' | 'warning' | 'error' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  content: string
  duration?: number
}

const state = reactive({
  toasts: [] as ToastItem[]
})

let idCounter = 0

const remove = (id: number) => {
  const index = state.toasts.findIndex(t => t.id === id)
  if (index !== -1) {
    state.toasts.splice(index, 1)
  }
}

const show = (content: string, type: ToastType = 'info', duration = 3000) => {
  const id = idCounter++
  const toast: ToastItem = { id, type, content, duration }

  state.toasts.push(toast)

  if (duration > 0) {
    setTimeout(() => {
      remove(id)
    }, duration)
  }
}

export const toast = {
  success: (msg: string, duration?: number) => show(msg, 'success', duration),
  warning: (msg: string, duration?: number) => show(msg, 'warning', duration),
  error: (msg: string, duration?: number) => show(msg, 'error', duration),
  info: (msg: string, duration?: number) => show(msg, 'info', duration),
  state,
  remove
}

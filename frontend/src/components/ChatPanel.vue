<script setup lang="ts">
import { ref, nextTick, onMounted, watch, createVNode, render } from 'vue'
import {
  Position, MagicStick, VideoPause,
  EditPen, RefreshRight, CopyDocument
} from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import { toast } from '@/utils/toast'
import { copyToClipboard } from '@/utils/clipboard'
import AuthImg from '@/components/AuthImg.vue'

const emit = defineEmits(['view-image'])

interface Message {
  role: 'user' | 'ai'
  content: string
  loading?: boolean
}

const messages = ref<Message[]>([])
const userInput = ref('')
const isLoading = ref(false)
const scrollRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
let abortController: AbortController | null = null

// Edit State
const editingIndex = ref<number | null>(null)
const editContent = ref('')

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true
})

const defaultImageRender = md.renderer.rules.image || function (tokens, idx, options, env, self) {
  return self.renderToken(tokens, idx, options)
}

md.renderer.rules.image = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  if (!token) return ''
  const src = token.attrGet('src') || ''
  const alt = token.content || 'Image'

  if (src.includes('/api/v1/images')) {
    return `<div class="chat-img-grid-item vue-auth-img-mount" data-src="${src}" data-alt="${alt}"></div>`
  }
  return defaultImageRender(tokens, idx, options, env, self)
}

const mountAuthImages = () => {
  if (!scrollRef.value) return

  const mountPoints = scrollRef.value.querySelectorAll('.vue-auth-img-mount')

  mountPoints.forEach((el) => {
    const element = el as HTMLElement
    if (el.hasAttribute('data-mounted')) return

    let src = el.getAttribute('data-src') || ''
    const alt = el.getAttribute('data-alt')

    const idMatch = src.match(/images\/(\d+)/)
    const imageId = (idMatch && idMatch[1]) ? parseInt(idMatch[1]) : null

    if (src) {
      if (src.startsWith('/api/v1')) {
        src = src.replace('/api/v1', '')
      }

      const vnode = createVNode(AuthImg, {
        src,
        alt: alt || 'Image',
        // fit: 'contain',
        style: { width: '100%', height: 'auto', display: 'block' }
      })

      element.style.minHeight = '0'
      element.style.height = 'auto'
      element.style.background = 'transparent'
      element.style.border = 'none'

      render(vnode, el)
      el.setAttribute('data-mounted', 'true')

      if (imageId) {
        element.style.cursor = 'pointer'
        element.onclick = (e) => {
          e.stopPropagation()
          emit('view-image', imageId)
        }
      }
    }
  })
}

// Auto Scroll & Mount Images
watch(messages, () => {
  nextTick(() => {
    if (scrollRef.value) {
      const div = scrollRef.value
      const isNearBottom = div.scrollHeight - div.scrollTop - div.clientHeight < 150
      const isNewLoading = messages.value[messages.value.length - 1]?.loading

      if (isNearBottom || isNewLoading) {
        div.scrollTo({ top: div.scrollHeight, behavior: 'smooth' })
      }
    }
    mountAuthImages()
  })
}, { deep: true })

// Core Actions
const handleSend = async (textOverride?: string) => {
  const text = textOverride || userInput.value.trim()
  if (!text || isLoading.value) return

  if (!textOverride) {
    messages.value.push({ role: 'user', content: text })
    userInput.value = ''
  }

  isLoading.value = true

  messages.value.push({ role: 'ai', content: '', loading: true })
  const currentAiMsg = messages.value[messages.value.length - 1]!

  abortController = new AbortController()
  const token = localStorage.getItem('access_token')

  try {
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ query: text }),
      signal: abortController.signal
    })

    if (!response.ok) {
      if (response.status === 401) toast.error('登录已过期')
      else toast.error(`Error: ${response.statusText}`)
      currentAiMsg.content = "抱歉，网络连接异常，请稍后重试。"
      return
    }

    if (!response.body) throw new Error('No body')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let done = false

    while (!done) {
      const { value, done: doneReading } = await reader.read()
      done = doneReading
      if (value) {
        const chunk = decoder.decode(value, { stream: true })
        currentAiMsg.content += chunk
        nextTick(mountAuthImages)
      }
    }
  } catch (error: unknown) {
    const e = error as Error
    if (e.name !== 'AbortError') {
      console.error(e)
      currentAiMsg.content += "\n[连接中断]"
    }
  } finally {
    isLoading.value = false
    currentAiMsg.loading = false
    abortController = null
    if (editingIndex.value === null) {
      nextTick(() => inputRef.value?.focus())
    }
    setTimeout(() => {
      if (scrollRef.value) {
        scrollRef.value.scrollTo({
          top: scrollRef.value.scrollHeight,
          behavior: 'smooth'
        })
      }
    }, 100)
  }
}

const handleStop = () => {
  if (abortController) {
    abortController.abort()
    abortController = null
    isLoading.value = false
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.role === 'ai') lastMsg.loading = false
  }
}

// Edit User Message
const startEdit = (index: number) => {
  if (isLoading.value) return
  editingIndex.value = index
  editContent.value = messages.value[index]!.content
}

const cancelEdit = () => {
  editingIndex.value = null
  editContent.value = ''
}

const updateMessage = (index: number) => {
  if (!editContent.value.trim()) return
  messages.value[index]!.content = editContent.value
  editingIndex.value = null
  if (index < messages.value.length - 1) {
    messages.value.splice(index + 1)
  }
  handleSend(editContent.value)
}

// Retry & Copy
const handleRetry = () => {
  if (isLoading.value) return
  const lastUserIndex = messages.value.length - 2
  if (lastUserIndex >= 0 && messages.value[lastUserIndex]!.role === 'user') {
    const text = messages.value[lastUserIndex]!.content
    messages.value.pop()
    handleSend(text)
  }
}

const handleCopy = async (content: string) => {
  try {
    await copyToClipboard(content)
    toast.success('已复制内容')
  } catch (e) {
    console.error(e)
    toast.error('复制失败')
  }
}

const isLastUserMessage = (index: number) => {
  const isLast = index === messages.value.length - 1
  const isSecondLast = index === messages.value.length - 2
  return (isLast || isSecondLast) && !isLoading.value
}

const isLastAiMessage = (index: number) => {
  if (index === 0) return false
  return index === messages.value.length - 1 && !isLoading.value
}

onMounted(() => {
  if (messages.value.length === 0) {
    messages.value.push({
      role: 'ai',
      content: '你好，我是你的智能相册助手。\n你可以描述想要查找的图片内容，例如：\n\n- "找找去年冬天的雪景"\n- "有没有关于猫的照片？"'
    })
  }
  nextTick(() => inputRef.value?.focus())
})
</script>

<template>
  <div class="chat-gemini-layout">

    <div ref="scrollRef" class="scroll-container custom-scroll">
      <div class="content-width-limiter">

        <div v-for="(msg, index) in messages" :key="index" class="message-block" :class="msg.role">

          <template v-if="msg.role === 'user'">
            <div class="user-row">
              <div v-if="isLastUserMessage(index) && editingIndex !== index" class="message-actions left">
                <div class="action-btn-circle" @click="startEdit(index)">
                  <el-icon>
                    <EditPen />
                  </el-icon>
                </div>
              </div>

              <div class="user-bubble-wrapper">
                <template v-if="editingIndex === index">
                  <div class="edit-mode-bubble">
                    <textarea v-model="editContent" rows="3" @keydown.enter.exact.prevent="updateMessage(index)"
                      @keydown.esc="cancelEdit"></textarea>
                  </div>

                  <div class="edit-footer-actions">
                    <div class="action-btn-circle danger" @click="cancelEdit">
                      <el-icon>
                        <Close />
                      </el-icon>
                    </div>
                    <div class="action-btn-circle primary" @click="updateMessage(index)">
                      <el-icon>
                        <Check />
                      </el-icon>
                    </div>
                  </div>
                </template>

                <div v-else class="user-bubble">
                  {{ msg.content }}
                </div>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="ai-response">
              <div class="ai-header">
                <div class="gemini-icon">
                  <el-icon>
                    <MagicStick />
                  </el-icon>
                </div>
                <span class="ai-name">Photo Assistant</span>
              </div>

              <div class="markdown-body" v-html="md.render(msg.content)"></div>

              <div v-if="msg.loading" class="thinking-loader">
                <span></span><span></span><span></span>
              </div>

              <div v-if="isLastAiMessage(index)" class="ai-footer-actions">

                <div class="action-btn-circle" @click="handleCopy(msg.content)">
                  <el-icon>
                    <CopyDocument />
                  </el-icon>
                </div>
                <div class="action-btn-circle" @click="handleRetry">
                  <el-icon>
                    <RefreshRight />
                  </el-icon>
                </div>
              </div>
            </div>
          </template>

        </div>

        <div class="spacer"></div>
      </div>
    </div>

    <div class="input-area-wrapper">
      <div class="input-container">
        <input ref="inputRef" v-model="userInput" type="text" placeholder="问问相册助手..." @keydown.enter="handleSend()"
          :disabled="isLoading" />

        <button class="send-fab" :class="{ 'is-loading': isLoading, 'has-content': userInput.trim() }"
          @click="isLoading ? handleStop() : handleSend()">
          <el-icon v-if="isLoading">
            <VideoPause />
          </el-icon>
          <el-icon v-else>
            <Position />
          </el-icon>
        </button>
      </div>

      <div class="footer-hint">
        由 RAG + LLM 驱动。内容由 AI 生成，请以实际图片为准。
      </div>
    </div>

  </div>
</template>

<style scoped lang="scss">
.chat-gemini-layout {
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 20px 0;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }

  mask-image: linear-gradient(to bottom, black 0%, black 85%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 0%, black 85%, transparent 100%);
}

.content-width-limiter {
  max-width: 768px;
  margin: 0 auto;
  padding-top: 60px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.user-row {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  gap: 12px;
  width: 100%;

  &:hover .message-actions {
    opacity: 1;
    transform: translateX(0);
  }
}

.message-actions {
  opacity: 0;
  transform: translateX(10px);
  transition: all 0.2s ease;
  padding-top: 10px;
}

.action-btn-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);

  &:hover {
    background: rgba(255, 255, 255, 0.15);
    color: var(--text-main);
    transform: scale(1.05);
    border-color: rgba(255, 255, 255, 0.2);
  }

  &:active {
    transform: scale(0.95);
  }
}

.user-bubble-wrapper {
  max-width: 80%;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 15px;
}

.user-bubble {
  background: #27272a;
  color: #f4f4f5;
  padding: 12px 20px;
  border-radius: 24px;
  font-size: 1rem;
  line-height: 1.6;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.edit-mode-bubble {
  background: #27272a;
  color: #f4f4f5;
  padding: 12px 20px;
  border-radius: 24px;
  font-size: 1rem;
  line-height: 1.6;
  border: 1px solid rgba(255, 255, 255, 0.05);

  width: 100%;
  min-width: 300px;
  display: flex;

  textarea {
    width: 100%;
    background: transparent;
    border: none;
    color: inherit;
    font-size: 1rem;
    line-height: 1.6;
    resize: none;
    outline: none;
    font-family: inherit;
    padding: 0;
    margin: 0;
  }
}

.edit-footer-actions {
  display: flex;
  gap: 12px;
}

.ai-response {
  display: flex;
  flex-direction: column;

  .ai-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;

    .gemini-icon {
      font-size: 20px;
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 0 8px rgba(79, 172, 254, 0.4));
      display: flex;
      align-items: center;
    }

    .ai-name {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-main);
      opacity: 0.9;
    }
  }
}

.ai-footer-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  opacity: 0.8;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
}

.input-area-wrapper {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  width: auto;
  padding: 0 20px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  z-index: 20;
  pointer-events: none;
  box-sizing: border-box;
}

.input-container {
  pointer-events: auto;
  width: 100%;
  max-width: 768px;
  height: 60px;
  border-radius: 30px;

  background: #1c1917;
  border: 1px solid var(--input-border);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);

  display: flex;
  align-items: center;
  padding: 0 8px 0 16px;

  transition: background-color 0.2s ease, box-shadow 0.2s ease;

  box-sizing: border-box;

  &:hover {
    background: #262626;
  }

  &:focus-within {
    transform: none;
    border-color: var(--input-border);
    background: #2a2a2a;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
  }

  input {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-main);
    font-size: 1rem;
    height: 100%;
    outline: none;
    min-width: 0;

    &::placeholder {
      color: var(--text-placeholder);
      transition: color 0.2s;
    }
  }

  &:focus-within input::placeholder {
    color: rgba(255, 255, 255, 0.15);
  }
}

@media (max-width: 640px) {
  .input-area-wrapper {
    padding: 0 16px 20px;
  }

  .input-container {
    height: 50px;
  }

  .scroll-container {
    padding: 10px 16px 0;
  }
}

.send-fab {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: all 0.2s;

  &.has-content,
  &.is-loading {
    background: var(--text-main);
    color: var(--bg-color);
  }

  &.is-loading:hover {
    background: #ef4444;
    color: white;
  }

  &:hover:not(.is-loading):not(.has-content) {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-main);
  }
}

.footer-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  opacity: 0.6;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

.spacer {
  height: 140px;
}

:deep(.markdown-body) {
  font-size: 1rem;
  line-height: 1.75;
  color: #e4e4e7;

  p {
    margin-bottom: 16px;
  }

  strong {
    color: #fff;
    font-weight: 600;
  }

  .thinking-loader {
    margin-top: 8px;
  }

  .chat-img-grid-item {
    margin: 16px 0;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: #000;
    max-width: 400px;
    transition: transform 0.3s;
    min-height: 200px;

    &:hover {
      transform: scale(1.01);
      // border-color: rgba(255, 255, 255, 0.2);
    }
  }
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.thinking-loader {
  display: flex;
  gap: 4px;
  padding: 4px 0;

  span {
    width: 5px;
    height: 5px;
    background: var(--text-muted);
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;

    &:nth-child(1) {
      animation-delay: -0.32s;
    }

    &:nth-child(2) {
      animation-delay: -0.16s;
    }
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes bounce {

  0%,
  80%,
  100% {
    transform: scale(0);
    opacity: 0.5;
  }

  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>

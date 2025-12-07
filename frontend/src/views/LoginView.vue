<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { toast } from '@/utils/toast'

import LoadingButton from '@/components/LoadingButton.vue'

const router = useRouter()
const userStore = useUserStore()

const isLogin = ref(true)
const hasSwitched = ref(false)
const loading = ref(false)
const isMobile = ref(false)

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', confirmPassword: '' })

// Responsive check
const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

/* 3D Tilt Logic */
const cardRef = ref<HTMLElement | null>(null)
const cardVars = reactive({
  '--mouse-x': '0px',
  '--mouse-y': '0px',
  '--rotate-x': '0deg',
  '--rotate-y': '0deg'
})
const clamp = (val: number, min: number, max: number) => Math.min(Math.max(val, min), max)

const handleMouseMove = (e: MouseEvent) => {
  // Disable 3D tilt on mobile for performance
  if (isMobile.value || !cardRef.value) return

  const rect = cardRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  cardVars['--mouse-x'] = `${x}px`
  cardVars['--mouse-y'] = `${y}px`

  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  const offsetX = e.clientX - centerX
  const offsetY = e.clientY - centerY

  const rotateY = clamp(offsetX / 40, -12, 12)
  const rotateX = clamp(-offsetY / 40, -12, 12)

  cardVars['--rotate-x'] = `${rotateX}deg`
  cardVars['--rotate-y'] = `${rotateY}deg`
}

const switchToRegister = () => {
  hasSwitched.value = true
  isLogin.value = false
}

const switchToLogin = () => {
  hasSwitched.value = true
  isLogin.value = true
}

const flipClass = computed(() => {
  if (!hasSwitched.value) return ''
  return isLogin.value ? 'anim-to-login' : 'anim-to-register'
})

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    toast.warning('请填写用户名和密码')
    return
  }
  if (loginForm.username.length < 6 || loginForm.password.length < 6) {
    toast.warning('用户名和密码长度至少为 6 位')
    return
  }
  loading.value = true
  try {
    await userStore.login(loginForm)
    router.push('/')
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  if (!registerForm.username || !registerForm.email || !registerForm.password || !registerForm.confirmPassword) {
    toast.warning('请填写所有必填项')
    return
  }
  if (registerForm.username.length < 6 || registerForm.password.length < 6) {
    toast.warning('用户名和密码长度至少为 6 位')
    return
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(registerForm.email)) {
    toast.warning('请输入有效的电子邮箱地址')
    return
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    toast.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await userStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })
    toast.success('注册成功，请登录')
    switchToLogin()
    registerForm.password = ''
    registerForm.confirmPassword = ''
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container" @mousemove="handleMouseMove">

    <div ref="cardRef" class="login-card-container" :style="cardVars">

      <div class="flip-wrapper" :class="flipClass">

        <div class="face front glass-panel">
          <div class="glow-border"></div>

          <div class="card-content">
            <div class="header">
              <div class="logo-wrapper">
                <h1>Photo<span class="highlight">Manager</span></h1>
              </div>
              <p class="subtitle">欢迎回来</p>
            </div>

            <div class="form-body">
              <div class="input-group">
                <el-input v-model="loginForm.username" placeholder="用户名" class="custom-input" :prefix-icon="User" />
              </div>
              <div class="input-group">
                <el-input v-model="loginForm.password" type="password" placeholder="密码" class="custom-input"
                  :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
              </div>
              <LoadingButton type="primary" style="margin-top: 12px; color: var(--text-main);" :loading="loading"
                @click="handleLogin">
                登 录
              </LoadingButton>
            </div>

            <div class="footer">
              <span class="text-muted">还没有账户？</span>
              <a class="text-link" style="margin-left: 6px;" @click="switchToRegister">去注册</a>
            </div>
          </div>
        </div>

        <div class="face back glass-panel">
          <div class="glow-border"></div>

          <div class="card-content">
            <div class="header">
              <div class="logo-wrapper">
                <h1>Photo<span class="highlight">Manager</span></h1>
              </div>
              <p class="subtitle">创建新账户</p>
            </div>

            <div class="form-body">
              <div class="input-group">
                <el-input v-model="registerForm.username" placeholder="用户名" class="custom-input" :prefix-icon="User" />
              </div>
              <div class="input-group">
                <el-input v-model="registerForm.email" placeholder="电子邮箱" class="custom-input" :prefix-icon="Message" />
              </div>
              <div class="input-group">
                <el-input v-model="registerForm.password" type="password" placeholder="密码" class="custom-input"
                  :prefix-icon="Lock" show-password />
              </div>
              <div class="input-group">
                <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" class="custom-input"
                  :prefix-icon="Lock" />
              </div>
              <LoadingButton type="primary" style="margin-top: 12px;" :loading="loading" @click="handleRegister">
                注 册
              </LoadingButton>
            </div>

            <div class="footer">
              <span class="text-muted">已经有账户了？</span>
              <a class="text-link" style="margin-left: 6px;" @click="switchToLogin">去登录</a>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1200px;
  width: 100vw;
  overflow: hidden;
}

.login-card-container {
  position: relative;
  width: 100%;
  max-width: 400px;
  background: transparent;

  /* Apply 3D Tilt on Desktop */
  transform: rotateX(var(--rotate-x)) rotateY(var(--rotate-y));
  transition: transform 0.1s linear;
  will-change: transform;
  transform-style: preserve-3d;
}

/* Mobile Adaptation */
@media (max-width: 768px) {
  .login-card-container {
    /* Disable 3D Tilt on mobile */
    transform: none !important;
    transition: none;
    width: 90vw;
    max-width: 90vw;
  }

  .login-container {
    perspective: none;
  }

  .card-content {
    padding: 32px 24px !important;
  }
}

.flip-wrapper {
  position: relative;
  width: 100%;
  display: grid;
  grid-template-areas: "stack";
  -webkit-transform-style: preserve-3d;
  transform-style: preserve-3d;
}

.flip-wrapper.anim-to-register {
  animation: flipToRegister 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.flip-wrapper.anim-to-login {
  animation: flipToLogin 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes flipToRegister {
  0% {
    transform: rotateY(0deg);
  }

  60% {
    transform: rotateY(185deg);
  }

  80% {
    transform: rotateY(177.5deg);
  }

  100% {
    transform: rotateY(180deg);
  }
}

@keyframes flipToLogin {
  0% {
    transform: rotateY(180deg);
  }

  60% {
    transform: rotateY(-5deg);
  }

  80% {
    transform: rotateY(2.5deg);
  }

  100% {
    transform: rotateY(0deg);
  }
}

.face {
  grid-area: stack;
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
  width: 100%;
  background: var(--bg-panel);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 24px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  justify-content: center;
  transform-style: preserve-3d;
  -webkit-transform-style: preserve-3d;
}

.front {
  transform: rotateY(0deg) translateZ(1px);
  z-index: 2;
}

.back {
  transform: rotateY(180deg) translateZ(1px);
  z-index: 1;
}

/* Glow Border Effect */
.glow-border {
  position: absolute;
  inset: 0;
  border-radius: 24px;
  padding: 1.5px;

  /* Dynamic mouse tracking on desktop*/
  background: radial-gradient(800px circle at var(--mouse-x) var(--mouse-y),
      rgba(255, 237, 213, 0.6),
      rgba(255, 255, 255, 0.1) 40%,
      transparent 80%);

  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  pointer-events: none;
  z-index: 10;
}

/* Mobile Static Glow */
@media (max-width: 768px) {
  .glow-border {
    background: linear-gradient(135deg,
        rgba(255, 237, 213, 0.4) 0%,
        rgba(255, 255, 255, 0.1) 30%,
        rgba(255, 255, 255, 0.05) 100%);
  }
}

.card-content {
  position: relative;
  z-index: 20;
  padding: 48px 36px;
}

.header {
  text-align: center;
  margin-bottom: 36px;

  h1 {
    font-size: 2rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.5px;
    color: var(--text-main);

    .highlight {
      background: linear-gradient(to right, #fbbf24, var(--primary-color));
      background-clip: text;
      -webkit-background-clip: text;
      color: transparent;
      -webkit-text-fill-color: transparent;
    }
  }

  .subtitle {
    color: var(--text-sub);
    margin-top: 6px;
    font-size: 0.9rem;
  }
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.footer {
  margin-top: 28px;
  text-align: center;
  font-size: 0.85rem;
}

:deep(.custom-input .el-input__wrapper) {
  background-color: var(--input-bg);
  box-shadow: 0 0 0 1px var(--input-border);
  border-radius: 10px;
  padding: 1px 15px;
  height: 46px;
}

:deep(.custom-input .el-input__inner) {
  color: var(--text-main);
}

:deep(.custom-input .el-input__wrapper.is-focus) {
  background-color: var(--input-focus-bg);
  box-shadow: 0 0 0 2px var(--primary-color);
}

.text-link {
  color: var(--primary-color);
  cursor: pointer;
  font-weight: 600;

  &:hover {
    color: #fbbf24;
  }
}

.text-muted {
  color: var(--text-sub);
  opacity: 0.8;
}
</style>

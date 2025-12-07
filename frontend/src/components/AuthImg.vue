<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import http from '@/utils/http'
import { Picture } from '@element-plus/icons-vue'

const props = defineProps<{
  src: string
  alt?: string
  fit?: 'cover' | 'contain' | 'fill'
}>()

const objectUrl = ref<string>('')
const loading = ref(true)
const error = ref(false)

const loadImage = async () => {
  if (!props.src) return

  loading.value = true
  error.value = false

  try {
    const response = await http.get(props.src, { responseType: 'blob' })
    objectUrl.value = URL.createObjectURL(response.data)
  } catch (e) {
    console.error('Image load failed:', e)
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(() => props.src, () => {
  if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
  loadImage()
})

onMounted(() => {
  loadImage()
})
</script>

<template>
  <div class="auth-img-container" :class="{ 'is-error': error }">
    <img v-if="objectUrl && !loading && !error" :src="objectUrl" :alt="alt" :style="{ objectFit: fit || 'cover' }" />

    <div v-if="loading" class="skeleton-loader">
      <div class="shimmer"></div>
    </div>

    <div v-if="error" class="error-placeholder">
      <el-icon :size="24">
        <Picture />
      </el-icon>
      <span>Failed</span>
    </div>
  </div>
</template>

<style scoped>
.auth-img-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: #27272a;
}

img {
  width: 100%;
  height: 100%;
  display: block;
  opacity: 0;
  animation: fadeIn 0.5s ease forwards;
}

@keyframes fadeIn {
  to {
    opacity: 1;
  }
}

.skeleton-loader {
  position: absolute;
  inset: 0;
  background: #27272a;
}

.shimmer {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg,
      transparent 0%,
      rgba(255, 255, 255, 0.05) 50%,
      transparent 100%);
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(100%);
  }
}

.error-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #52525b;
  gap: 8px;
  font-size: 12px;
}
</style>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'

interface Blob {
  id: number
  x: number
  y: number
  vx: number
  vy: number
  size: number
  color: string
  opacity: number
  life: number
  maxLife: number
}

const route = useRoute()
const blobs = ref<Blob[]>([])

const isActive = ref(true)
const isFullyStopped = ref(false)

let blobCounter = 0
let animationFrameId: number | null = null
let spawnTimer: number | null = null
let stopTimeout: number | null = null

const colors = [
  '#f59e0b',
  '#ea580c',
  '#fbbf24',
  '#ef4444'
]

const randomRange = (min: number, max: number) => Math.random() * (max - min) + min

const createBlob = () => {
  // Limit max blobs to prevent performance issues
  if (!isActive.value || blobs.value.length > 12) return

  const size = randomRange(300, 600)
  const randomColor = colors[Math.floor(Math.random() * colors.length)] ?? '#409eff'

  blobs.value.push({
    id: blobCounter++,
    x: randomRange(-200, window.innerWidth),
    y: randomRange(-200, window.innerHeight),
    vx: randomRange(-0.2, 0.2),
    vy: randomRange(-0.2, 0.2),
    size: size,
    color: randomColor,
    opacity: 0,
    life: 0,
    maxLife: randomRange(600, 1200)
  })
}

const animate = () => {
  // Do not calculate if page is not present
  if (document.hidden || isFullyStopped.value) {
    animationFrameId = requestAnimationFrame(animate)
    return
  }

  let totalVelocity = 0

  for (let i = blobs.value.length - 1; i >= 0; i--) {
    const b = blobs.value[i]
    if (!b) continue

    if (isActive.value) {
      // Active
      b.vx += randomRange(-0.02, 0.02)
      b.vy += randomRange(-0.02, 0.02)

      const maxSpeed = 1.5
      b.vx = Math.max(Math.min(b.vx, maxSpeed), -maxSpeed)
      b.vy = Math.max(Math.min(b.vy, maxSpeed), -maxSpeed)

      b.life++

      if (b.life < 100) {
        b.opacity += 0.005
        if (b.opacity > 0.5) b.opacity = 0.5
      }
      else if (b.life > b.maxLife - 100) {
        b.opacity -= 0.005
      }

      if (b.life >= b.maxLife || b.opacity <= 0) {
        blobs.value.splice(i, 1)
        continue
      }

    } else {
      // Inactive
      b.vx *= 0.995
      b.vy *= 0.995

      if (b.opacity < 0.5) b.opacity += 0.005
    }

    b.x += b.vx
    b.y += b.vy

    // Bounce at border
    if (b.x < -300) b.vx += 0.05
    if (b.x > window.innerWidth - b.size + 300) b.vx -= 0.05
    if (b.y < -300) b.vy += 0.05
    if (b.y > window.innerHeight - b.size + 300) b.vy -= 0.05

    totalVelocity += Math.abs(b.vx) + Math.abs(b.vy)
  }

  if (!isActive.value && totalVelocity < 0.01) {
    isFullyStopped.value = true
  }

  animationFrameId = requestAnimationFrame(animate)
}

const startSpawning = () => {
  if (!spawnTimer) {
    createBlob()
    spawnTimer = setInterval(createBlob, 2000)
  }
}

const stopSpawning = () => {
  if (spawnTimer) {
    clearInterval(spawnTimer)
    spawnTimer = null
  }
}

watch(() => route.name, (newRouteName) => {
  if (stopTimeout) {
    clearTimeout(stopTimeout)
    stopTimeout = null
  }

  if (newRouteName === 'login') {
    isActive.value = true
    isFullyStopped.value = false
    startSpawning()
    if (!animationFrameId) animate()
  } else {
    stopTimeout = window.setTimeout(() => {
      isActive.value = false
      stopSpawning()
    }, 2000)
  }
}, { immediate: true })

/**
 * Handle Page Visibility Change
 * Pauses animation loop when tab is backgrounded to save resources.
 */
const handleVisibilityChange = () => {
  if (document.hidden) {
    stopSpawning()
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
  } else {
    if (isActive.value) {
      startSpawning()
    }

    if (!isFullyStopped.value && !animationFrameId) {
      animate()
    }
  }
}

onMounted(() => {
  // Initial population
  for (let i = 0; i < 5; i++) createBlob()

  animate()
  spawnTimer = setInterval(createBlob, 2000)

  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (spawnTimer) clearInterval(spawnTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="blobs-container">
    <div v-for="blob in blobs" :key="blob.id" class="blob" :style="{
      transform: `translate3d(${blob.x}px, ${blob.y}px, 0)`,
      width: `${blob.size}px`,
      height: `${blob.size}px`,
      background: `radial-gradient(circle, ${blob.color} 0%, transparent 70%)`,
      opacity: blob.opacity
    }"></div>
  </div>
</template>

<style scoped>
.blobs-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  pointer-events: none;
  overflow: hidden;
  background-color: var(--bg-color);
  transform: translateZ(0);
}

.blob {
  position: absolute;
  top: 0;
  left: 0;
  background: radial-gradient(circle, var(--blob-color) 0%, transparent 70%);
  will-change: transform, opacity;
  transform: translateZ(0);
}
</style>

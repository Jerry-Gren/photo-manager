<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

import BackgroundBlobs from '@/components/BackgroundBlobs.vue'
import ToastManager from '@/components/ToastManager.vue'

const userStore = useUserStore()
const route = useRoute()

onMounted(async () => {
  if (userStore.token && !userStore.user) {
    try {
      await userStore.fetchProfile()
    } catch (e) {
      console.error('Session restoration failed', e)
    }
  }
})
</script>

<template>
  <BackgroundBlobs />
  <div class="app-tint-layer"></div>
  <RouterView v-slot="{ Component }">
    <Transition name="page-fade">
      <component :is="Component" :key="route.path" />
    </Transition>
  </RouterView>
  <ToastManager />
</template>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  padding: 0;
  background-color: transparent;
  overflow: hidden;
}

.app-tint-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-color: rgba(15, 15, 17, 0.6);
}

.page-fade-enter-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  will-change: transform, opacity;
  z-index: 2;
}

.page-fade-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  will-change: transform, opacity;
  z-index: 1;
}

.page-fade-enter-from {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: scale(1.03);
}
</style>

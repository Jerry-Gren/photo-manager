<script setup lang="ts">
defineOptions({
  inheritAttrs: false
})

defineProps<{
  loading?: boolean
  disabled?: boolean
}>()
</script>

<template>
  <el-button class="warm-btn" v-bind="$attrs" :loading="false" :disabled="loading || disabled">
    <span class="btn-content-wrapper">
      <span class="btn-text" :class="{ 'is-hidden': loading }">
        <slot></slot>
      </span>

      <div class="btn-loader" :class="{ 'is-visible': loading }">
        <div class="dots-loading">
          <span></span><span></span><span></span>
        </div>
      </div>
    </span>
  </el-button>
</template>

<style scoped lang="scss">
.btn-content-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.btn-text {
  transition: opacity 0.3s ease, transform 0.3s ease;
  opacity: 1;
  transform: scale(1);
}

.btn-text.is-hidden {
  opacity: 0;
  transform: scale(0.8);
}

.btn-loader {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.8);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  white-space: nowrap;
}

.btn-loader.is-visible {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
}

.dots-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.dots-loading span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: #fff;
  border-radius: 50%;
  animation: dotJump 1.4s infinite ease-in-out both;
}

.dots-loading span:nth-child(1) {
  animation-delay: -0.32s;
}

.dots-loading span:nth-child(2) {
  animation-delay: -0.16s;
}

.dots-loading span:nth-child(3) {
  animation-delay: 0s;
}

@keyframes dotJump {

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

:deep(.el-button.is-disabled),
:deep(.el-button.is-disabled:hover),
:deep(.el-button.is-disabled:focus) {
  background-color: var(--el-color-primary) !important;
  border-color: var(--el-color-primary) !important;
  opacity: 0.8;
  color: #fff !important;
}
</style>

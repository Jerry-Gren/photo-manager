<script setup lang="ts">
import { toast } from '@/utils/toast'
import {
  CircleCheckFilled,
  CircleCloseFilled,
  WarningFilled,
  InfoFilled,
  Close
} from '@element-plus/icons-vue'

const icons = {
  success: CircleCheckFilled,
  warning: WarningFilled,
  error: CircleCloseFilled,
  info: InfoFilled
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast-list">
        <div v-for="item in toast.state.toasts" :key="item.id" class="toast-item glass-panel"
          :class="`type-${item.type}`">
          <div class="accent-bar"></div>

          <el-icon class="icon" :size="20">
            <component :is="icons[item.type]" />
          </el-icon>

          <div class="content">{{ item.content }}</div>

          <div class="close-btn" @click="toast.remove(item.id)">
            <el-icon>
              <Close />
            </el-icon>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.toast-container {
  position: fixed;
  top: 24px;
  left: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 9999;
  gap: 12px;
  pointer-events: none;
}

.toast-item {
  pointer-events: auto;
  display: flex;
  align-items: center;
  width: fit-content;
  min-width: 320px;
  max-width: 450px;
  padding: 12px 16px;
  background: rgba(30, 30, 30, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  color: #fafaf9;
  font-size: 14px;
  font-weight: 500;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  transform: translateZ(0);
  backface-visibility: hidden;
  perspective: 1000px;
  will-change: transform, opacity;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.accent-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: currentColor;
}

.icon {
  margin-right: 12px;
  flex-shrink: 0;
}

.content {
  flex: 1;
  line-height: 1.4;
  color: var(--text-main);
}

.close-btn {
  margin-left: 12px;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.2s;
  display: flex;
  align-items: center;

  &:hover {
    opacity: 1;
  }
}

.type-success {
  color: #10b981;

  .accent-bar {
    background-color: #10b981;
    box-shadow: 0 0 10px #10b981;
  }
}

.type-warning {
  color: #f59e0b;

  .accent-bar {
    background-color: #f59e0b;
    box-shadow: 0 0 10px #f59e0b;
  }
}

.type-error {
  color: #ef4444;

  .accent-bar {
    background-color: #ef4444;
    box-shadow: 0 0 10px #ef4444;
  }
}

.type-info {
  color: #3b82f6;

  .accent-bar {
    background-color: #3b82f6;
    box-shadow: 0 0 10px #3b82f6;
  }
}

.toast-list-move,
.toast-list-enter-active,
.toast-list-leave-active {
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  z-index: 1;
}

.toast-list-enter-from {
  opacity: 0;
  transform: translateY(-30px) scale(0.9);
}

.toast-list-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.toast-list-leave-active {
  position: absolute;
  left: 0;
  right: 0;
  margin: 0 auto;
  width: fit-content;
  z-index: -1;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, type CSSProperties } from 'vue'
import { Calendar, ArrowLeft, ArrowRight, ArrowLeftBold, ArrowRightBold, Close } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: Date | null
  placeholder?: string
}>()

const emit = defineEmits(['update:modelValue'])

const isVisible = ref(false)
const triggerRef = ref<HTMLElement | null>(null)
const popupRef = ref<HTMLElement | null>(null)

const popupStyle = ref<CSSProperties>({
  position: 'fixed',
  top: '0px',
  left: '0px',
  width: 'auto',
  zIndex: 9999,
  boxSizing: 'border-box'
})

// Calendar State
const currentCursor = ref(new Date())

const initCursor = () => {
  if (props.modelValue) {
    currentCursor.value = new Date(props.modelValue)
  } else {
    currentCursor.value = new Date()
  }
}

// Formatters
const formatDate = (d: Date | null) => {
  if (!d) return ''
  const y = d.getFullYear()
  const m = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  return `${y}/${m}/${day}`
}

const headerTitle = computed(() => {
  const y = currentCursor.value.getFullYear()
  const m = currentCursor.value.getMonth() + 1
  return `${y} 年 ${m} 月`
})

// Calendar Logic
const days = computed(() => {
  const year = currentCursor.value.getFullYear()
  const month = currentCursor.value.getMonth()

  const firstDayOfMonth = new Date(year, month, 1)
  const lastDayOfMonth = new Date(year, month + 1, 0)

  const startDay = firstDayOfMonth.getDay()
  const daysInMonth = lastDayOfMonth.getDate()

  const result = []

  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = 0; i < startDay; i++) {
    result.push({
      date: new Date(year, month - 1, prevMonthLastDay - startDay + 1 + i),
      isCurrentMonth: false
    })
  }

  for (let i = 1; i <= daysInMonth; i++) {
    result.push({
      date: new Date(year, month, i),
      isCurrentMonth: true
    })
  }

  const remaining = 42 - result.length
  for (let i = 1; i <= remaining; i++) {
    result.push({
      date: new Date(year, month + 1, i),
      isCurrentMonth: false
    })
  }

  return result
})

const isSelected = (d: Date) => {
  if (!props.modelValue) return false
  return d.toDateString() === props.modelValue.toDateString()
}

const isToday = (d: Date) => {
  return d.toDateString() === new Date().toDateString()
}

// Actions
const handleSelect = (d: Date) => {
  emit('update:modelValue', d)
  isVisible.value = false
}

const handleClear = (e: Event) => {
  e.stopPropagation()
  emit('update:modelValue', null)
}

const navMonth = (delta: number) => {
  const newDate = new Date(currentCursor.value)
  newDate.setMonth(newDate.getMonth() + delta)
  currentCursor.value = newDate
}

const navYear = (delta: number) => {
  const newDate = new Date(currentCursor.value)
  newDate.setFullYear(newDate.getFullYear() + delta)
  currentCursor.value = newDate
}

// Dropdown Logic
const updatePosition = () => {
  if (triggerRef.value) {
    const rect = triggerRef.value.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const isMobile = viewportWidth < 768

    if (isMobile) {
      const padding = 20
      popupStyle.value = {
        position: 'fixed',
        top: `${rect.bottom + 8}px`,
        left: `${padding}px`,
        width: `${viewportWidth - (padding * 2)}px`,
        zIndex: 9999,
        boxSizing: 'border-box'
      }
    } else {
      const desiredWidth = Math.max(rect.width, 300)
      let leftPos = rect.left
      let finalWidth = desiredWidth

      if (leftPos + finalWidth > viewportWidth - 20) {
        leftPos = rect.right - finalWidth
      }

      if (leftPos < 20) {
        leftPos = 20
        finalWidth = viewportWidth - 40
      }

      popupStyle.value = {
        position: 'fixed',
        top: `${rect.bottom + 8}px`,
        left: `${leftPos}px`,
        width: `${finalWidth}px`,
        zIndex: 9999,
        boxSizing: 'border-box'
      }
    }
  }
}

const toggle = () => {
  if (isVisible.value) {
    isVisible.value = false
  } else {
    initCursor()
    updatePosition()
    isVisible.value = true
  }
}

const handleClickOutside = (e: MouseEvent) => {
  if (
    isVisible.value &&
    triggerRef.value &&
    !triggerRef.value.contains(e.target as Node) &&
    popupRef.value &&
    !popupRef.value.contains(e.target as Node)
  ) {
    isVisible.value = false
  }
}

const handleResize = () => {
  if (isVisible.value) updatePosition()
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('resize', handleResize)
  window.addEventListener('scroll', handleResize, true)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('scroll', handleResize, true)
})
</script>

<template>
  <div ref="triggerRef" class="date-trigger" :class="{ 'is-active': isVisible, 'has-value': !!modelValue }"
    @click="toggle">
    <el-icon class="prefix-icon">
      <Calendar />
    </el-icon>
    <span class="value-text" v-if="modelValue">{{ formatDate(modelValue) }}</span>
    <span class="placeholder" v-else>{{ placeholder || '选择日期' }}</span>

    <div class="clear-btn" v-if="modelValue" @click="handleClear">
      <el-icon>
        <Close />
      </el-icon>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="zoom-fade">
      <div v-if="isVisible" ref="popupRef" class="date-popup glass-panel" :style="popupStyle">
        <div class="calendar-header">
          <div class="nav-group">
            <button class="nav-btn" @click="navYear(-1)"><el-icon>
                <ArrowLeftBold />
              </el-icon></button>
            <button class="nav-btn" @click="navMonth(-1)"><el-icon>
                <ArrowLeft />
              </el-icon></button>
          </div>
          <span class="header-title">{{ headerTitle }}</span>
          <div class="nav-group">
            <button class="nav-btn" @click="navMonth(1)"><el-icon>
                <ArrowRight />
              </el-icon></button>
            <button class="nav-btn" @click="navYear(1)"><el-icon>
                <ArrowRightBold />
              </el-icon></button>
          </div>
        </div>

        <div class="calendar-weeks">
          <span v-for="w in ['日', '一', '二', '三', '四', '五', '六']" :key="w">{{ w }}</span>
        </div>

        <div class="calendar-grid">
          <div v-for="(day, idx) in days" :key="idx" class="day-cell" :class="{
            'not-current': !day.isCurrentMonth,
            'today': isToday(day.date),
            'selected': isSelected(day.date)
          }" @click="handleSelect(day.date)">
            <span class="day-num">{{ day.date.getDate() }}</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
.date-trigger {
  width: 100%;
  height: 40px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  position: relative;

  box-sizing: border-box;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
  }

  &.is-active {
    background: rgba(255, 255, 255, 0.06);
    border-color: var(--primary-color);
    box-shadow: 0 0 0 1px var(--primary-color);
  }

  .prefix-icon {
    font-size: 16px;
    color: var(--text-muted);
    margin-right: 8px;
  }

  .value-text {
    font-size: 0.85rem;
    color: var(--text-main);
    font-weight: 500;
  }

  .placeholder {
    font-size: 0.85rem;
    color: var(--text-placeholder);
  }

  .clear-btn {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    transition: all 0.2s;
    opacity: 0;

    &:hover {
      background: rgba(255, 255, 255, 0.2);
      color: var(--text-main);
    }
  }

  &:hover .clear-btn {
    opacity: 1;
  }
}

.date-popup {
  position: fixed;
  z-index: 9999;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 300px;

  box-sizing: border-box;
  overflow: hidden;

  background: rgba(23, 22, 20, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  border-radius: 16px;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .header-title {
    color: var(--text-main);
    font-weight: 600;
    font-size: 0.95rem;
  }

  .nav-group {
    display: flex;
    gap: 4px;
  }

  .nav-btn {
    width: 24px;
    height: 24px;
    border: none;
    background: transparent;
    color: var(--text-secondary);
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    font-size: 12px;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      color: var(--text-main);
    }
  }
}

.calendar-weeks {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  justify-items: center;
  margin-bottom: 4px;

  span {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-weight: 600;
    height: 32px;
    line-height: 32px;
  }
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  row-gap: 4px;
  justify-items: center;
}

.day-cell {
  width: 100%;
  aspect-ratio: 1 / 1;
  height: auto;
  max-width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  font-size: 0.85rem;
  color: var(--text-secondary);
  border-radius: 50%;
  transition: color 0.2s;

  &::before {
    content: '';
    position: absolute;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background-color: var(--primary-color);
    opacity: 0;
    transform: scale(0.8);
    transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
    z-index: -1;
  }

  &:hover:not(.selected) {
    color: var(--text-main);

    &::before {
      opacity: 0.15;
      transform: scale(1);
    }
  }

  &.not-current {
    color: rgba(255, 255, 255, 0.15);

    &:hover {
      color: var(--text-muted);
    }
  }

  &.today {
    color: var(--primary-color);
    font-weight: 700;

    &::after {
      content: '';
      position: absolute;
      bottom: 4px;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background-color: var(--primary-color);
    }
  }

  &.selected {
    color: var(--text-main);

    &::before {
      opacity: 1;
      transform: scale(1);
      box-shadow: 0 4px 12px rgba(var(--primary-color-rgb), 0.4);
    }

    &.today {
      color: var(--text-main);
    }

    &.today::after {
      background-color: var(--text-main);
    }
  }
}

.zoom-fade-enter-active,
.zoom-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.zoom-fade-enter-from,
.zoom-fade-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}
</style>

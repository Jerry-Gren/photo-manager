<script setup lang="ts">
import { reactive, watch } from 'vue'
import { Refresh, Filter, Sort, Calendar, } from '@element-plus/icons-vue'
import CustomDatePicker from '@/components/CustomDatePicker.vue'

defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits(['update:modelValue', 'change'])

// Filter State
const filters = reactive({
  startDate: null as Date | null,
  endDate: null as Date | null,

  dateField: 'taken_at' as 'taken_at' | 'uploaded_at',
  sortOrder: 'desc' as 'asc' | 'desc',
  sortBy: 'uploaded_at' as 'uploaded_at' | 'taken_at' | 'file_size' | 'resolution'
})

// Computed Text for UI
const getAscText = (type: string) => {
  if (type === 'file_size' || type === 'resolution') return '从小到大'
  return '旧的在前'
}

const getDescText = (type: string) => {
  if (type === 'file_size' || type === 'resolution') return '从大到小'
  return '新的在前'
}

// Actions
const handleApply = () => {
  emit('change', {
    start_date: filters.startDate,
    end_date: filters.endDate,
    date_field: filters.dateField,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder
  })
}

const handleReset = () => {
  filters.startDate = null
  filters.endDate = null
  filters.dateField = 'taken_at'
  filters.sortOrder = 'desc'
  filters.sortBy = 'uploaded_at'
  handleApply()
}

watch(() => [filters.sortOrder, filters.sortBy], () => {
  handleApply()
})
</script>

<template>
  <div class="filter-panel-wrapper" :class="{ 'is-expanded': modelValue }">
    <div class="filter-glass-container">
      <div class="filter-inner-content">
        <div class="filter-layout">

          <div class="filter-section time-section">
            <div class="section-header">
              <el-icon>
                <Calendar />
              </el-icon>
              <span>时间范围</span>
            </div>

            <div class="control-wrapper column-mode">

              <div class="custom-date-row">
                <CustomDatePicker v-model="filters.startDate" placeholder="开始日期" />
              </div>

              <div class="custom-date-row">
                <CustomDatePicker v-model="filters.endDate" placeholder="结束日期" />
              </div>

              <div class="sort-grid">
                <div class="sort-option" :class="{ active: filters.dateField === 'taken_at' }"
                  @click="filters.dateField = 'taken_at'">
                  拍摄日期
                </div>
                <div class="sort-option" :class="{ active: filters.dateField === 'uploaded_at' }"
                  @click="filters.dateField = 'uploaded_at'">
                  上传日期
                </div>
              </div>

            </div>
          </div>

          <div class="filter-section sort-section">
            <div class="section-header">
              <el-icon>
                <Sort />
              </el-icon>
              <span>排序逻辑</span>
            </div>

            <div class="control-wrapper column-mode">
              <div class="sort-grid">
                <div class="sort-option" :class="{ active: filters.sortBy === 'uploaded_at' }"
                  @click="filters.sortBy = 'uploaded_at'">
                  上传时间
                </div>
                <div class="sort-option" :class="{ active: filters.sortBy === 'taken_at' }"
                  @click="filters.sortBy = 'taken_at'">
                  拍摄时间
                </div>
                <div class="sort-option" :class="{ active: filters.sortBy === 'file_size' }"
                  @click="filters.sortBy = 'file_size'">
                  文件大小
                </div>
                <div class="sort-option" :class="{ active: filters.sortBy === 'resolution' }"
                  @click="filters.sortBy = 'resolution'">
                  分辨率
                </div>
              </div>

              <div class="sort-order-toggle" @click="filters.sortOrder = filters.sortOrder === 'asc' ? 'desc' : 'asc'">
                <span :class="{ active: filters.sortOrder === 'asc' }">
                  {{ getAscText(filters.sortBy) }}
                </span>
                <div class="toggle-track">
                  <div class="toggle-thumb" :class="filters.sortOrder">
                    <el-icon v-if="filters.sortOrder === 'asc'">
                      <Sort />
                    </el-icon>
                    <el-icon v-else class="flip-icon">
                      <Sort />
                    </el-icon>
                  </div>
                </div>
                <span :class="{ active: filters.sortOrder === 'desc' }">
                  {{ getDescText(filters.sortBy) }}
                </span>
              </div>
            </div>
          </div>

        </div>

        <div class="filter-footer">
          <div class="active-summary">
            <template v-if="filters.startDate || filters.endDate">
              <span class="dot"></span>
              已应用时间筛选
            </template>
          </div>
          <div class="action-buttons">
            <button class="text-btn" @click="handleReset">
              <el-icon>
                <Refresh />
              </el-icon> 重置
            </button>
            <button class="primary-btn" @click="handleApply">
              <el-icon>
                <Filter />
              </el-icon> 确认筛选
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.filter-panel-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  opacity: 0;
  transform: translateY(-12px);
  padding: 0;
  margin-bottom: 0;

  --bounce-curve: cubic-bezier(0.18, 0.89, 0.32, 1.15);
  --anim-duration: 0.8s;

  transition:
    grid-template-rows var(--anim-duration) var(--bounce-curve),
    margin-bottom var(--anim-duration) var(--bounce-curve),
    padding var(--anim-duration) var(--bounce-curve),
    transform var(--anim-duration) var(--bounce-curve),
    opacity 0.6s ease;

  z-index: 10;
  position: relative;
  will-change: grid-template-rows, margin-bottom, padding, transform, opacity;

  &.is-expanded {
    grid-template-rows: 1fr;
    opacity: 1;
    transform: translateY(0);
    margin-bottom: 32px;
    padding: 4px;
  }
}

.filter-glass-container {
  overflow: hidden;
  min-height: 0;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.4);
  padding: 0;
}

.filter-inner-content {
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.filter-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    gap: 32px;
  }
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 8px;

  .el-icon {
    font-size: 1.1rem;
    color: var(--text-secondary);
  }
}

.control-wrapper {
  display: flex;
  width: 100%;

  &.column-mode {
    flex-direction: column;
    gap: 12px;
  }
}

.custom-date-row {
  width: 100%;
  height: 40px;
}

.sort-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 100%;
}

.sort-option {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 0;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;

  text-align: center;
  font-size: 0.85rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
  }

  &.active {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-main);
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(var(--primary-color-rgb), 0.3);
  }
}

.sort-order-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0 16px;
  height: 38px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.06);
  }

  span {
    font-size: 0.85rem;
    color: var(--text-muted);
    transition: color 0.2s;

    &.active {
      color: var(--text-main);
      font-weight: 500;
    }
  }

  .toggle-track {
    width: 36px;
    height: 20px;
    background: rgba(0, 0, 0, 0.4);
    border-radius: 10px;
    position: relative;
    margin: 0 12px;
  }

  .toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    background: var(--text-secondary);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.3s;

    .el-icon {
      font-size: 10px;
      color: #000;
      font-weight: bold;
    }

    &.desc {
      transform: translateX(16px);
      background: var(--primary-color);

      .el-icon {
        color: var(--text-main);
      }
    }

    .flip-icon {
      transform: scaleY(-1);
    }
  }
}

.filter-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.active-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--primary-color);
  min-height: 20px;

  .dot {
    width: 6px;
    height: 6px;
    background: currentColor;
    border-radius: 50%;
    box-shadow: 0 0 8px currentColor;
  }
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-left: auto;
}

.text-btn {
  height: 40px;
  padding: 0 20px;
  border-radius: 10px;

  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);

  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 500;

  transition: all 0.2s ease;

  &:hover {
    color: var(--text-main);
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
  }

  &:active {
    background: rgba(255, 255, 255, 0.03);
  }
}

.primary-btn {
  height: 40px;
  padding: 0 28px;
  border-radius: 10px;

  background: var(--primary-color);
  border: none;
  color: white;

  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 600;
  font-size: 0.9rem;

  box-shadow: none;
  transition: all 0.2s ease;

  &:hover {
    background: var(--primary-hover);
  }

  &:active {
    background: var(--primary-active);
  }
}

:deep(.premium-date-input) {
  width: 100% !important;
  height: 40px !important;
}

:deep(.premium-date-input .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.03) !important;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08) !important;
  border-radius: 10px !important;
  padding: 0 16px !important;
  height: 40px !important;
  transition: all 0.2s;
}

:deep(.premium-date-input .el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.2) !important;
}

:deep(.premium-date-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-color) !important;
  background: rgba(255, 255, 255, 0.06) !important;
}

:deep(.premium-date-input .el-input__inner) {
  color: var(--text-main) !important;
  font-size: 0.85rem !important;
  height: 40px !important;
  line-height: 40px !important;
  cursor: pointer !important;
}

:deep(.premium-date-input .el-input__prefix) {
  color: var(--text-muted);
}
</style>

<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted, onUnmounted } from 'vue'
import { Plus, Refresh, Delete, Document } from '@element-plus/icons-vue'
import LoadingButton from '@/components/LoadingButton.vue'
import { imageApi } from '@/api/image'
import { toast } from '@/utils/toast'

import { ACCEPT_EXTENSIONS, isWebSafeImage } from '@/utils/file'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits(['update:modelValue', 'success'])

const visible = ref(false)
const dragActive = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const isMobile = ref(false)
const previewLoadError = ref(false)

// Form State
const file = ref<File | null>(null)
const previewUrl = ref<string>('')
const form = reactive({
  title: '',
  description: ''
})

// Responsive Check
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

// Sync visibility
watch(() => props.modelValue, (val) => {
  visible.value = val
  if (!val) {
    // Short delay to clear form after animation ends
    setTimeout(() => resetForm(), 300)
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const resetForm = () => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  file.value = null
  previewUrl.value = ''
  form.title = ''
  form.description = ''
  uploading.value = false
  previewLoadError.value = false
}

// Dialog Width Calculation
const dialogWidth = computed(() => {
  return isMobile.value ? '90%' : '750px' // Desktop wider for side-by-side
})

// File Handling
const handleFileSelect = (selectedFile: File) => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)

  file.value = selectedFile
  previewLoadError.value = false
  if (isWebSafeImage(selectedFile.type)) {
    previewUrl.value = URL.createObjectURL(selectedFile)
  } else {
    previewUrl.value = ''
  }

  // Auto-fill title
  const name = selectedFile.name.substring(0, selectedFile.name.lastIndexOf('.'))
  if (!form.title) form.title = name
}

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    handleFileSelect(target.files[0])
  }
  // Reset input so same file can be selected again if needed
  target.value = ''
}

const triggerFileInput = () => {
  if (!uploading.value) fileInputRef.value?.click()
}

// Drag & Drop
const onDragEnter = (e: DragEvent) => { e.preventDefault(); if (!uploading.value) dragActive.value = true }
const onDragLeave = (e: DragEvent) => { e.preventDefault(); dragActive.value = false }
const onDrop = (e: DragEvent) => {
  e.preventDefault()
  dragActive.value = false
  if (!uploading.value && e.dataTransfer?.files && e.dataTransfer.files[0]) {
    handleFileSelect(e.dataTransfer.files[0])
  }
}

// Submit
const handleUpload = async () => {
  if (!file.value) return

  uploading.value = true
  try {
    await imageApi.upload(file.value, form.title, form.description)
    toast.success('上传成功')
    emit('success')
    visible.value = false
  } catch (e) {
    console.error(e)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="上传新图片" :width="dialogWidth" align-center append-to-body
    class="upload-dialog glass-dialog" :close-on-click-modal="!uploading" :show-close="!uploading">
    <div class="upload-layout">

      <div class="layout-left">
        <div class="drop-zone" :class="{ 'is-dragover': dragActive, 'has-file': !!file, 'is-loading': uploading }"
          @dragenter.prevent="onDragEnter" @dragover.prevent="onDragEnter" @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop" @click="!file && triggerFileInput()">
          <input ref="fileInputRef" type="file" :accept="ACCEPT_EXTENSIONS" style="display: none"
            @change="onFileChange" />

          <div v-if="uploading" class="uploading-overlay">
            <div class="radar-spinner"></div>
            <span>Processing...</span>
          </div>

          <template v-if="!file">
            <div class="icon-circle">
              <el-icon>
                <Plus />
              </el-icon>
            </div>
            <div class="upload-text">点击或拖拽上传</div>
            <div class="upload-hint">支持 JPG PNG GIF WebP</div>
            <div class="upload-hint">HEIF TIFF BMP JXL AVIF RAW</div>
          </template>

          <template v-else>
            <img v-if="previewUrl && !previewLoadError" :src="previewUrl" class="preview-img"
              @error="previewLoadError = true" />
            <div v-else class="file-placeholder">
              <div class="file-icon-card">
                <el-icon :size="32">
                  <Document />
                </el-icon>
                <span class="ext-badge">{{ file?.name.split('.').pop()?.toUpperCase() }}</span>
              </div>
              <div class="file-name">{{ file?.name }}</div>
              <div class="file-size">{{ (file!.size / 1024 / 1024).toFixed(2) }} MB</div>
            </div>
            <div class="preview-actions-bar">
              <div class="action-item" @click.stop="triggerFileInput">
                <el-icon :size="16">
                  <Refresh />
                </el-icon>
                <span class="tooltip">更换图片</span>
              </div>
              <div class="divider"></div>
              <div class="action-item is-danger" @click.stop="resetForm">
                <el-icon :size="16">
                  <Delete />
                </el-icon>
                <span class="tooltip">移除</span>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div class="layout-right">
        <div class="form-header" v-if="!isMobile">
          <h3>图片信息</h3>
          <p>完善信息以便于检索和管理</p>
        </div>

        <div class="meta-form" :class="{ 'disabled': uploading }">
          <div class="form-item">
            <label>标题 <span class="required">*</span></label>
            <el-input v-model="form.title" placeholder="例如：杭州西湖日落" class="custom-input" :disabled="uploading" />
          </div>
          <div class="form-item">
            <label>描述</label>
            <el-input v-model="form.description" type="textarea" :rows="5" placeholder="关于这张照片的故事..."
              class="custom-input textarea-mode" resize="none" :disabled="uploading" />
          </div>
        </div>

        <div class="dialog-footer-inline">
          <el-button class="cancel-btn" @click="visible = false" :disabled="uploading">取消</el-button>
          <LoadingButton class="submit-btn" :loading="uploading" @click="handleUpload" :disabled="!file || !form.title">
            确认上传
          </LoadingButton>
        </div>
      </div>

    </div>
  </el-dialog>
</template>

<style lang="scss">
.glass-dialog {
  background: rgba(23, 22, 20, 0.85) !important;
  backdrop-filter: blur(24px) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 20px !important;
  box-shadow: 0 40px 80px rgba(0, 0, 0, 0.6) !important;
  padding: 0 !important;
  overflow: hidden;

  .el-dialog__header {
    margin: 0;
    padding: 20px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);

    .el-dialog__title {
      color: var(--text-main);
      font-size: 1.1rem;
      font-weight: 600;
    }
  }

  .el-dialog__body {
    padding: 0 !important;
  }

  .el-dialog__headerbtn:hover .el-dialog__close {
    color: var(--primary-color);
  }
}
</style>

<style scoped lang="scss">
.upload-layout {
  display: flex;
  padding: 24px;
  gap: 32px;
  min-height: 380px;

  @media (max-width: 768px) {
    flex-direction: column;
    gap: 20px;
    padding: 20px;
    min-height: auto;
  }
}

.layout-left {
  flex: 1.2;
  display: flex;
  flex-direction: column;
}

.layout-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.drop-zone {
  width: 100%;
  height: 100%;
  flex: 1;

  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
  overflow: hidden;

  @media (max-width: 768px) {
    height: auto;
    flex: none;
    aspect-ratio: 16/9;
  }

  &:hover:not(.has-file):not(.is-loading) {
    border-color: var(--primary-color);
    background: rgba(var(--primary-color-rgb), 0.05);

    .icon-circle {
      transform: scale(1.1);
      border-color: var(--primary-color);
      color: var(--primary-color);
    }
  }

  &.is-dragover {
    border-color: var(--primary-color);
    background: rgba(249, 115, 22, 0.1);
    transform: scale(1.02);
  }

  &.has-file {
    border: 2px solid rgba(255, 255, 255, 0.1);
    background: transparent;
  }
}

.icon-circle {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  transition: all 0.3s ease;
}

.upload-text {
  color: var(--text-main);
  font-weight: 500;
  font-size: 15px;
}

.upload-hint {
  color: var(--text-muted);
  font-size: 13px;
  margin-top: 6px;
}

.preview-img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;

  object-fit: contain;

  background: transparent;

  z-index: 1;
}

.preview-actions {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transform: translateY(-10px);
  transition: all 0.2s ease;
  z-index: 10;
}

.drop-zone:hover .preview-actions {
  opacity: 1;
  transform: translateY(0);
}

.preview-actions-bar {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;

  display: flex;
  align-items: center;
  justify-content: center;

  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.12);

  padding: 4px;
  border-radius: 20px;
  gap: 4px;

  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);

  opacity: 0;
  transform: translateY(-10px) scale(0.95);
  pointer-events: none;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.drop-zone:hover .preview-actions-bar {
  opacity: 1;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

.divider {
  width: 1px;
  height: 14px;
  background: rgba(255, 255, 255, 0.15);
  margin: 0 2px;
}

.action-item {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e4e4e7;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #fff;

    .tooltip {
      opacity: 1;
      transform: translateY(100%) translateX(-50%);
    }
  }

  &:active {
    background: rgba(255, 255, 255, 0.05);
  }

  &.is-danger:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }
}

.tooltip {
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateY(110%) translateX(-50%) scale(0.8);
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
  font-weight: 500;

  &::before {
    content: '';
    position: absolute;
    top: -4px;
    left: 50%;
    transform: translateX(-50%);
    border-width: 0 4px 4px 4px;
    border-style: solid;
    border-color: transparent transparent rgba(0, 0, 0, 0.8) transparent;
  }
}

.uploading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(2px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-main);
  gap: 16px;
  z-index: 10;
}

.radar-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.form-header {
  margin-bottom: 20px;

  h3 {
    margin: 0;
    font-size: 1.1rem;
    color: var(--text-main);
  }

  p {
    margin: 4px 0 0;
    font-size: 0.85rem;
    color: var(--text-muted);
  }
}

.meta-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;

  &.disabled {
    opacity: 0.5;
    pointer-events: none;
  }
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;

  label {
    font-size: 0.9rem;
    color: var(--text-secondary);
    font-weight: 500;

    .required {
      color: #ef4444;
    }
  }
}

.dialog-footer-inline {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.cancel-btn {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  color: var(--text-secondary) !important;
  border-radius: 10px;
  height: 42px;
  padding: 0 24px;
  font-weight: 500;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    color: var(--text-main) !important;
    border-color: rgba(255, 255, 255, 0.3) !important;
  }
}

.submit-btn {
  height: 42px;
  padding: 0 28px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-main) !important;

  transition: all 0.2s ease !important;

  :deep(span) {
    color: var(--text-main) !important;
    transition: color 0.2s ease;
  }

  &:disabled,
  &.is-disabled {
    opacity: 0.8;
    border-color: transparent !important;

    :deep(span) {
      color: rgba(255, 255, 255, 0.6) !important;
    }
  }
}

.file-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-main);
  gap: 8px;
  animation: fadeIn 0.3s ease;
}

.file-icon-card {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.ext-badge {
  position: absolute;
  bottom: -6px;
  background: var(--primary-color);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.file-name {
  font-size: 13px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.9;
}

.file-size {
  font-size: 12px;
  color: var(--text-muted);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  Close, Check, Download, Delete,
  MagicStick, Edit, Plus,
  ZoomIn, ZoomOut, ArrowLeft, ArrowRight
} from '@element-plus/icons-vue'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'

import { imageApi } from '@/api/image'
import { toast } from '@/utils/toast'
import http from '@/utils/http'
import { copyToClipboard } from '@/utils/clipboard'
import type { ImageMeta } from '@/types'
import AuthImg from './AuthImg.vue'
import LoadingButton from './LoadingButton.vue'
import { isWebSafeImage } from '@/utils/file'

const props = withDefaults(defineProps<{
  modelValue: boolean
  imageId: number | null
  showNav?: boolean
}>(), {
  showNav: true
})

const emit = defineEmits(['update:modelValue', 'refresh', 'delete', 'prev', 'next'])

const isVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const detail = ref<ImageMeta | null>(null)
const isZoomed = ref(false)
const isMobile = ref(false)
const cleanupTimer = ref<ReturnType<typeof setTimeout> | null>(null)

// Edit State
const isEditing = ref(false)
const editLoading = ref(false)
const cropperImgRef = ref<HTMLImageElement | null>(null)
const cropperInstance = ref<Cropper | null>(null)
const editImageUrl = ref('')
const isCropperReady = ref(false)
const isHoveringStage = ref(false)
const activeFilter = ref('')

const availableFilters = [
  { name: '无', value: '', css: '' },
  { name: '黑白', value: 'grayscale', css: 'grayscale(100%)' },
  { name: '复古', value: 'sepia', css: 'sepia(100%)' },
  { name: '高亮', value: 'brightness', css: 'brightness(130%)' },
  { name: '高对比', value: 'contrast', css: 'contrast(150%)' },
  { name: '反色', value: 'invert', css: 'invert(100%)' }
]

const formatDate = (d?: string) => d ? new Date(d).toLocaleString('zh-CN', { hour12: false }) : '--'

const displayExif = computed(() => {
  if (!detail.value) return []

  const list: { label: string; value: string }[] = []
  const d = detail.value

  if (d.taken_at) {
    list.push({ label: '拍摄时间', value: formatDate(d.taken_at) })
  }

  if (d.resolution_width && d.resolution_height) {
    list.push({ label: '分辨率', value: `${d.resolution_width} x ${d.resolution_height}` })
  }

  if (d.location_name) {
    list.push({ label: '拍摄地点', value: d.location_name })
  }

  if (d.exif_data) {
    const data = detail.value.exif_data as Record<string, string | number>

    const add = (label: string, val: string | number | undefined) => {
      if (val !== undefined && val !== null && val !== '') {
        list.push({ label, value: String(val) })
      }
    }

    add('设备', data.Model)
    add('制造商', data.Make)
    add('镜头', data.LensModel || data.LensID)
    add('光圈', data.FNumber)
    add('快门', data.ExposureTime)
    add('ISO', data.ISOSpeedRatings)
    add('焦距', data.FocalLength)
    add('35mm等效焦距', data.FocalLengthIn35mmFilm)
    add('闪光灯', data.Flash)
    add('曝光补偿', data.ExposureBiasValue)
    add('艺术家', data.Artist)
    add('版权', data.Copyright)
  }

  return list
})

// Tag Input
const newTagInput = ref('')
const inputVisible = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)
const vFocus = {
  mounted: (el: HTMLElement) => el.focus()
}

const aiTags = computed(() => {
  if (!detail.value || !detail.value.tags) return []
  return detail.value.tags.filter(t => t.tag_type === 'ai_generated')
})

const displayTags = computed(() => {
  if (!detail.value || !detail.value.tags) return []

  const hiddenTypes = ['ai_generated', 'derived_time', 'exif_location']

  return detail.value.tags.filter(tag => !hiddenTypes.includes(tag.tag_type))
})

const bindKeys = () => window.addEventListener('keydown', handleKeydown)
const unbindKeys = () => window.removeEventListener('keydown', handleKeydown)
watch(
  [() => props.imageId, isVisible],
  ([newId, newVisible], [oldId, oldVisible]) => {

    if (newVisible) {
      if (cleanupTimer.value) {
        clearTimeout(cleanupTimer.value)
        cleanupTimer.value = null
      }

      if (!oldVisible) {
        bindKeys()
      }

      if (newId && (!oldVisible || newId !== oldId)) {
        fetchDetail(newId)
      }
    }

    if (oldVisible && !newVisible) {
      unbindKeys()
      closeEditMode()

      cleanupTimer.value = setTimeout(() => {
        detail.value = null
        isZoomed.value = false
        cleanupTimer.value = null
      }, 300)
    }
  }
)

const checkMobile = () => { isMobile.value = window.innerWidth < 768 }

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  if (isVisible.value) bindKeys()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  unbindKeys()
})

const fetchDetail = async (id: number) => {
  loading.value = true
  try {
    const res = await imageApi.getDetail(id)
    detail.value = res.data
  } catch (e) {
    console.error(e)
    toast.error('获取详情失败')
    isVisible.value = false
  } finally {
    loading.value = false
  }
}

const displayUrl = computed(() => {
  if (!detail.value) return ''

  if (isEditing.value) {
    return isWebSafeImage(detail.value.mime_type)
      ? imageApi.getOriginalUrl(detail.value.id)
      : imageApi.getThumbnailUrl(detail.value.id)
  }

  if (isWebSafeImage(detail.value.mime_type)) {
    return imageApi.getOriginalUrl(detail.value.id)
  } else {
    return imageApi.getThumbnailUrl(detail.value.id)
  }
})

const toggleZoom = () => {
  if (isEditing.value) return
  isZoomed.value = !isZoomed.value
}

const enterEditMode = async () => {
  if (!detail.value) return
  isEditing.value = true
  isCropperReady.value = false
  activeFilter.value = ''

  try {
    let targetUrl = ''
    if (isWebSafeImage(detail.value.mime_type)) {
      targetUrl = imageApi.getOriginalUrl(detail.value.id)
    } else {
      targetUrl = imageApi.getThumbnailUrl(detail.value.id)
    }

    const res = await http.get(targetUrl, { responseType: 'blob' })
    editImageUrl.value = URL.createObjectURL(res.data)

    setTimeout(() => {
      if (cropperImgRef.value) {
        cropperInstance.value = new Cropper(cropperImgRef.value, {
          viewMode: 1,
          dragMode: 'move',
          autoCropArea: 0.8,
          restore: false,
          guides: true,
          center: true,
          highlight: false,
          background: false,
          cropBoxMovable: true,
          cropBoxResizable: true,
          toggleDragModeOnDblclick: false,
          ready() {
            isCropperReady.value = true
          }
        })
      }
    }, 1000)
  } catch (e) {
    console.error(e)
    toast.error('加载失败')
    isEditing.value = false
  }
}

const saveEdit = async () => {
  if (!cropperInstance.value || !detail.value) return
  editLoading.value = true

  const data = cropperInstance.value.getData()
  const payload = {
    crop: {
      x: Math.round(data.x),
      y: Math.round(data.y),
      width: Math.round(data.width),
      height: Math.round(data.height)
    },
    filter: activeFilter.value || undefined
  }

  try {
    const res = await imageApi.edit(detail.value.id, payload)
    toast.success('裁剪成功')
    detail.value = res.data
    isZoomed.value = false
    closeEditMode()
    emit('refresh')
    await fetchDetail(detail.value.id)
  } catch (e) {
    console.error(e)
    toast.error('保存失败')
  } finally {
    editLoading.value = false
  }
}

const closeEditMode = () => {
  isEditing.value = false
  isCropperReady.value = false
  cropperInstance.value?.destroy()
  cropperInstance.value = null
  if (editImageUrl.value) URL.revokeObjectURL(editImageUrl.value)
  editImageUrl.value = ''
}

const handleDownload = () => {
  if (!detail.value) return
  const url = imageApi.getOriginalUrl(detail.value.id)
  http.get(url, { responseType: 'blob' }).then((res) => {
    const blobUrl = URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = detail.value?.original_filename || 'download.jpg'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(blobUrl)
  }).catch(() => toast.error('下载失败'))
}

const handleDelete = () => {
  ElMessageBox.confirm('确定要移入回收站吗？', '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
    customClass: 'glass-message-box'
  }).then(async () => {
    if (!detail.value) return
    try {
      await imageApi.delete(detail.value.id)
      toast.success('已删除')
      emit('delete', detail.value.id)
      isVisible.value = false
    } catch (e) { console.error(e) }
  })
}

const handleKeydown = (e: KeyboardEvent) => {
  if (isEditing.value) return
  if (!props.showNav) return
  if (e.key === 'ArrowLeft') emit('prev')
  if (e.key === 'ArrowRight') emit('next')
}

// Tags & Utils
const handleCloseTag = async (tagId: number) => {
  if (!detail.value) return
  try {
    await imageApi.removeTag(detail.value.id, tagId)
    detail.value.tags = detail.value.tags.filter(t => t.id !== tagId)
  } catch (e) { console.error(e) }
}
const showInput = () => { inputVisible.value = true }
const handleInputCancel = () => {
  inputVisible.value = false
  newTagInput.value = ''
}
const handleInputConfirm = async () => {
  if (!newTagInput.value.trim() || !detail.value) {
    handleInputCancel()
    return
  }

  try {
    await imageApi.addTag(detail.value.id, newTagInput.value.trim())
    toast.success('标签已添加')
    await fetchDetail(detail.value.id)
  } catch (e) {
    console.error(e)
  } finally {
    handleInputCancel()
  }
}

const handleCopy = async (text: string | number, type: string) => {
  if (!text) return
  try {
    await copyToClipboard(String(text))
    toast.success(`已复制 ${type}`)
  } catch (e) {
    console.error(e)
    toast.error('复制失败')
  }
}

const formatSize = (b: number) => {
  if (b === 0) return '0 B'
  const k = 1024, i = Math.floor(Math.log(b) / Math.log(k))
  return parseFloat((b / Math.pow(k, i)).toFixed(2)) + ' ' + ['B', 'KB', 'MB', 'GB'][i]
}

const showDock = computed(() => {
  if (!detail.value) return false
  return isMobile.value || isHoveringStage.value
})
</script>

<template>
  <el-dialog v-model="isVisible" class="glass-modal-xl" :show-close="false" align-center append-to-body
    destroy-on-close>
    <div class="modal-layout" v-if="detail">

      <div class="left-stage" @mouseenter="isHoveringStage = true" @mouseleave="isHoveringStage = false">

        <div class="stage-header">
          <div class="file-info">
            <span class="fname">{{ detail.original_filename }}</span>
          </div>
          <div class="close-icon" @click="isVisible = false">
            <el-icon>
              <Close />
            </el-icon>
          </div>
        </div>

        <div class="canvas-viewport" @click.self="!isEditing && toggleZoom()">

          <Transition name="pure-fade" mode="out-in">

            <div v-if="!isEditing" key="view" class="img-container" :class="{ 'zoomed': isZoomed }"
              @click="!isEditing && toggleZoom()">
              <AuthImg :src="displayUrl" fit="contain" class="display-img" />
            </div>

            <div v-else key="edit" class="cropper-host">
              <div class="cropper-wrapper" :class="{ 'is-visible': isCropperReady }"
                :style="{ '--active-filter': availableFilters.find(f => f.value === activeFilter)?.css || 'none' }">
                <img ref="cropperImgRef" :src="editImageUrl" />
              </div>
            </div>

          </Transition>
        </div>

        <div class="nav-btn prev" @click.stop="emit('prev')" v-if="!isEditing && showNav">
          <el-icon>
            <ArrowLeft />
          </el-icon>
        </div>

        <div class="nav-btn next" @click.stop="emit('next')" v-if="!isEditing && showNav">
          <el-icon>
            <ArrowRight />
          </el-icon>
        </div>

        <div class="floating-dock" :class="{ 'dock-hidden': !showDock }">
          <Transition name="dock-fade" mode="out-in">

            <div v-if="!isEditing" key="view" class="dock-layout-wrapper">
              <div class="dock-pill">
                <el-tooltip content="缩放" placement="top" :hide-after="0">
                  <button class="icon-btn" @click="toggleZoom">
                    <el-icon v-if="!isZoomed">
                      <ZoomIn />
                    </el-icon>
                    <el-icon v-else>
                      <ZoomOut />
                    </el-icon>
                  </button>
                </el-tooltip>


                <div class="divider"></div>

                <el-tooltip content="下载" placement="top" :hide-after="0">
                  <button class="icon-btn" @click="handleDownload">
                    <el-icon>
                      <Download />
                    </el-icon>
                  </button>
                </el-tooltip>

                <el-tooltip content="编辑" placement="top" :hide-after="0">
                  <button class="icon-btn" @click="enterEditMode">
                    <el-icon>
                      <Edit />
                    </el-icon>
                  </button>
                </el-tooltip>

                <div class="divider"></div>

                <el-tooltip content="删除" placement="top" :hide-after="0">
                  <button class="icon-btn danger" @click="handleDelete">
                    <el-icon>
                      <Delete />
                    </el-icon>
                  </button>
                </el-tooltip>
              </div>
            </div>

            <div v-else key="edit" class="dock-layout-wrapper">
              <div class="filter-bar">
                <div v-for="filter in availableFilters" :key="filter.value" class="filter-item"
                  :class="{ active: activeFilter === filter.value }" @click="activeFilter = filter.value">
                  <div class="preview-bubble" :style="{ filter: filter.css }">
                    <div class="sample-color"></div>
                  </div>
                  <span class="filter-name">{{ filter.name }}</span>
                </div>
              </div>

              <div class="dock-pill">
                <button class="icon-btn" @click="closeEditMode">
                  <el-icon>
                    <Close />
                  </el-icon>
                </button>
                <LoadingButton class="dock-confirm-btn" @click="saveEdit" :loading="editLoading">
                  <el-icon>
                    <Check />
                  </el-icon>
                </LoadingButton>
              </div>
            </div>


          </Transition>
        </div>
      </div>

      <div class="right-sidebar custom-scroll">
        <div class="sidebar-content">

          <div class="meta-header">
            <h2 class="title">{{ detail.title || '无标题' }}</h2>
            <div class="status-tag" :class="detail.status">{{ detail.status }}</div>
          </div>

          <div class="ai-block" v-if="aiTags.length > 0">
            <div class="ai-label">
              <el-icon>
                <MagicStick />
              </el-icon> AI 识别
            </div>

            <div class="ai-tags">
              <!-- 注意：这里遍历的是计算属性 aiTags -->
              <span v-for="t in aiTags" :key="t.id">#{{ t.name }}</span>
            </div>
          </div>

          <div class="info-group">
            <label>描述</label>
            <p class="text-val">{{ detail.description || '暂无描述...' }}</p>
          </div>

          <div class="info-group">
            <label>标签</label>
            <TransitionGroup name="tag-list" tag="div" class="tags-container">
              <div v-for="tag in displayTags" :key="tag.id" class="tag-item clickable"
                @click="handleCopy(tag.name, '标签')">
                {{ tag.name }}
                <el-icon v-if="tag.tag_type === 'user'" class="del" @click.stop="handleCloseTag(tag.id)">
                  <Close />
                </el-icon>
              </div>

              <div class="add-tag-btn" key="add-btn">
                <Transition name="tag-input" mode="out-in">
                  <input v-if="inputVisible" key="input" ref="inputRef" v-model="newTagInput" v-focus
                    @blur="handleInputCancel" @keyup.enter="handleInputConfirm" placeholder="输入标签..." />

                  <span v-else key="button" @click="showInput">
                    <el-icon style="margin-right: 4px; font-size: 14px;">
                      <Plus />
                    </el-icon> 新建标签
                  </span>
                </Transition>
              </div>
            </TransitionGroup>
          </div>

          <div class="info-group">
            <label>EXIF 信息</label>
            <div class="exif-grid" v-if="displayExif.length > 0">
              <div class="exif-item" v-for="(item, index) in displayExif" :key="index"
                @click="handleCopy(item.value, item.label)">
                <span class="label">{{ item.label }}</span>
                <span class="value" :title="item.value">{{ item.value }}</span>
              </div>
            </div>

          </div>

          <div class="file-meta-footer">
            ID: {{ detail.id }} • {{ formatSize(detail.file_size) }}
          </div>



        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style lang="scss">
.glass-modal-xl {
  width: 90vw;
  max-width: 1400px;
  height: 85vh;
  margin: 0 auto;

  background: rgba(23, 22, 20, 0.85) !important;
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 20px !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
  overflow: hidden;
  padding: 0;

  .el-dialog__header {
    display: none;
  }

  .el-dialog__body {
    padding: 0 !important;
    height: 100%;
  }
}

@media (max-width: 768px) {
  .glass-modal-xl {
    width: 100vw !important;
    height: 100vh !important;
    border-radius: 0 !important;
    border: none;
  }
}
</style>

<style scoped lang="scss">
.modal-layout {
  display: flex;
  width: 100%;
  height: 100%;

  @media (max-width: 768px) {
    flex-direction: column;
    overflow-y: auto;
  }
}

.left-stage {
  flex: 1;
  min-width: 0;
  height: 100%;
  position: relative;
  background-color: #121212;
  background-image:
    linear-gradient(45deg, #18181b 25%, transparent 25%),
    linear-gradient(-45deg, #18181b 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #18181b 75%),
    linear-gradient(-45deg, transparent 75%, #18181b 75%);
  background-size: 24px 24px;
  background-position: 0 0, 0 12px, 12px -12px, -12px 0px;
  display: flex;
  flex-direction: column;

  @media (max-width: 768px) {
    height: 60vh;
    flex: none;
  }
}

.stage-header {
  height: 80px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  pointer-events: none;

  .file-info {
    pointer-events: auto;
    background: rgba(30, 30, 30, 0.8);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    padding: 8px 16px;
    border-radius: 24px;
    font-size: 13px;
    color: var(--text-main);
    font-weight: 500;
    display: flex;
    align-items: center;
    transition: all 0.2s ease;
    max-width: 60%;
    flex-shrink: 1;
    min-width: 0;

    .fname {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: block;
    }

    &:hover {
      background: rgba(40, 40, 40, 0.8);
      border-color: rgba(255, 255, 255, 0.2);
    }
  }

  .close-icon {
    pointer-events: auto;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(30, 30, 30, 0.8);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-main);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.5, 1);
    font-size: 20px;

    &:hover {
      background: rgba(40, 40, 40, 0.9);
      border-color: rgba(255, 255, 255, 0.3);
      transform: scale(1.1);
    }

    &:active {
      background: rgba(66, 66, 66, 0.9);
      transform: scale(0.9);
    }
  }
}

.canvas-viewport {
  flex: 1;
  width: 100%;
  height: 100%;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 40px;
  box-sizing: border-box;
  overflow: hidden;
}

.img-container {
  width: 100%;
  height: 100%;

  display: flex;
  align-items: center;
  justify-content: center;

  cursor: zoom-in;
  position: relative;

  :deep(.auth-img-container) {
    width: 100%;
    height: 100%;
    background: transparent;

    display: flex;
    align-items: center;
    justify-content: center;
  }

  :deep(img) {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    object-fit: contain;

    box-shadow: 0 5px 30px rgba(0, 0, 0, 0.5);
    border-radius: 4px;
    transition: box-shadow 0.3s ease, border-radius 0.3s ease;
  }

  &.zoomed {
    width: calc(100% + 80px);
    height: calc(100% + 80px);
    margin: -40px;

    cursor: zoom-out;
    z-index: 10;

    :deep(img) {
      width: 100%;
      height: 100%;
      max-width: none;
      max-height: none;

      object-fit: cover;

      box-shadow: none;
      border-radius: 0;
    }
  }
}

.pure-fade-enter-active,
.pure-fade-leave-active {
  transition: opacity 0.4s ease;
}

.pure-fade-enter-from,
.pure-fade-leave-to {
  opacity: 0;
}

.cropper-host {
  width: calc(100% + 80px);
  height: calc(100% + 80px);
  margin: -40px;
  position: relative;
  overflow: hidden;

  .cropper-wrapper {
    width: 100%;
    height: 100%;

    background: #000;

    opacity: 0;
    transition: opacity 0.4s ease-in-out;

    --active-filter: none;

    &.is-visible {
      opacity: 1;
    }

    :deep(.cropper-container img) {
      filter: var(--active-filter) !important;
    }
  }

  img {
    display: block;
    max-width: 100%;
    opacity: 0 !important;
  }

  :deep(.cropper-container) {
    width: 100% !important;
    height: 100% !important;
    display: flex;
    justify-content: center;
    align-items: center;
  }
}

.nav-btn {
  position: absolute;
  top: 50%;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  z-index: 20;

  background: rgba(30, 30, 30, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);

  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);

  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-main);
  font-size: 24px;
  cursor: pointer;

  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);

  opacity: 0;
  transform: translate3d(0, -50%, 0) scale(0.8);

  &.prev {
    left: 24px;
    transform: translate3d(-20px, -50%, 0) scale(0.8);
  }

  &.next {
    right: 24px;
    transform: translate3d(20px, -50%, 0) scale(0.8);
  }

  &:hover {
    background: rgba(60, 60, 60, 0.8);
    border-color: rgba(255, 255, 255, 0.3);

    transform: translate3d(0, -50%, 0) scale(1.1) !important;
  }

  &:active {
    transform: translate3d(0, -50%, 0) scale(0.95) !important;
  }
}

.left-stage:hover .nav-btn {
  opacity: 1;

  &.prev {
    transform: translate3d(0, -50%, 0) scale(1);
  }

  &.next {
    transform: translate3d(0, -50%, 0) scale(1);
  }
}

.floating-dock {
  position: absolute;
  bottom: 24px;
  width: 100%;
  display: flex;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
}

.dock-layout-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;

  pointer-events: none;
  width: 100%;
}

.dock-layout-wrapper>* {
  pointer-events: auto;
}

.dock-fade-enter-active {
  transition: opacity 0.25s ease;
  transition-delay: 0.5s;
}

.dock-fade-leave-active {
  transition: opacity 0.25s ease;
}

.dock-fade-enter-from,
.dock-fade-leave-to {
  opacity: 0;
}

.filter-bar {
  pointer-events: auto;
  display: flex;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(30, 30, 30, 0.6);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  max-width: 90%;
  overflow-x: auto;

  &::-webkit-scrollbar {
    display: none;
  }

  .filter-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    opacity: 0.6;
    transition: all 0.2s;

    &:hover {
      opacity: 0.9;
    }

    &.active {
      opacity: 1;
      transform: scale(1.05);

      .preview-bubble {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.3);
      }

      .filter-name {
        color: var(--primary-color);
      }
    }
  }

  .preview-bubble {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    overflow: hidden;
    border: 2px solid rgba(255, 255, 255, 0.2);
    background: #333;
    transition: all 0.2s;

    .sample-color {
      width: 100%;
      height: 100%;
      background: linear-gradient(45deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%);
    }
  }

  .filter-name {
    font-size: 10px;
    color: #aaa;
    font-weight: 500;
    white-space: nowrap;
  }
}

.dock-pill {
  pointer-events: auto;
  background: rgba(30, 30, 30, 0.8);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 6px 12px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);

  .divider {
    width: 1px;
    height: 16px;
    background: rgba(255, 255, 255, 0.15);
    margin: 0 4px;
  }

  .icon-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: var(--text-secondary);
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;

    &:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.1);
    }

    &.danger:hover {
      color: #ef4444;
      background: rgba(239, 68, 68, 0.15);
    }

    &.primary-text {
      color: var(--primary-color);

      &:hover {
        background: rgba(249, 115, 22, 0.1);
      }
    }

    &:active {
      opacity: 0.8;
    }
  }
}

.dock-pill,
.filter-bar {
  will-change: transform, opacity;
  backface-visibility: hidden;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  opacity: 1;
  // transform: translate3d(0, 0, 0);
}

.floating-dock.dock-hidden .dock-pill,
.floating-dock.dock-hidden .filter-bar {
  opacity: 0;
  transform: translate3d(0, 0, 0);
  pointer-events: none;
}

.right-sidebar {
  width: 360px;
  flex-shrink: 0;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(24, 24, 27, 0.5);
  overflow-y: auto;

  @media (max-width: 768px) {
    width: 100%;
    border-left: none;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    min-height: 400px;
  }
}

.sidebar-content {
  padding: 30px 24px;
}

.meta-header {
  margin-bottom: 24px;

  .title {
    font-size: 1.4rem;
    margin: 0 0 8px;
    line-height: 1.3;
    color: var(--text-main);
  }

  .status-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;

    font-size: 0.85rem;
    font-weight: 600;
    text-transform: capitalize;

    padding: 0;
    border: none;
    background: transparent;

    &::before {
      content: '';
      display: block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: currentColor;
    }

    color: #71717a;

    &.active {
      color: #10b981;
    }

    &.processing {
      color: #3b82f6;

      &::before {
        animation: pulse-opacity 1.5s infinite ease-in-out;
      }
    }

    &.failed {
      color: #ef4444;
    }

    &.archived {
      color: #f59e0b;
    }
  }

  @keyframes pulse-opacity {

    0%,
    100% {
      opacity: 1;
    }

    50% {
      opacity: 0.4;
    }
  }
}

.ai-block {
  background: linear-gradient(180deg, rgba(139, 92, 246, 0.1), transparent);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;

  .ai-label {
    color: #c4b5fd;
    font-weight: 600;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .ai-desc {
    color: #e4e4e7;
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0 0 10px;
  }

  .ai-tags span {
    color: #a78bfa;
    font-size: 0.8rem;
    margin-right: 8px;
  }
}

.info-group {
  margin-bottom: 24px;

  label {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-muted);
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 12px;
  }

  .text-val {
    color: var(--text-secondary);
    font-size: 0.9rem;
  }
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  position: relative;

  --tag-height: 32px;

  .tag-item {
    min-height: var(--tag-height);
    padding: 0 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    line-height: 1.3;

    background: rgba(255, 255, 255, 0.06);
    color: var(--text-secondary);
    border: 1px solid rgba(255, 255, 255, 0.08);

    display: inline-flex;
    align-items: center;
    gap: 8px;

    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.5, 1);
    box-sizing: border-box;
    white-space: normal;
    word-break: break-word;
    max-width: 100%;
    position: relative;

    cursor: pointer;
    user-select: none;

    &:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.3);
      transform: scale(1.02);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      color: var(--text-main);
    }

    &:active {
      transform: scale(0.96);
      background: rgba(255, 255, 255, 0.08);
      box-shadow: none;
    }

    .del {
      flex-shrink: 0;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 10px;

      background: rgba(255, 255, 255, 0.1);
      color: rgba(255, 255, 255, 0.6);
      transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

      &:hover {
        background: #ef4444;
        color: var(--text-main);
        transform: scale(1.1);
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.4);
      }
    }
  }

  .add-tag-btn {
    display: inline-flex;
    height: var(--tag-height);
    align-items: center;
    vertical-align: top;
    transition: all 0.2s ease;

    span {
      height: 100%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 14px;

      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 20px;

      color: var(--text-secondary);
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      transition: all 0.2s;
      box-sizing: border-box;
      white-space: nowrap;
      background: transparent;

      &:hover {
        color: var(--primary-color);
        border-color: var(--primary-color);
        background: rgba(var(--primary-color-rgb), 0.08);
        transform: scale(1.02);
        box-shadow: 0 0 10px rgba(var(--primary-color-rgb), 0.15);
      }

      &:active {
        transform: scale(0.96);
      }
    }

    input {
      height: 100%;
      width: 120px;

      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--primary-color);
      border-radius: 20px;

      color: var(--text-secondary);
      padding: 0 14px;
      outline: none;
      font-size: 0.85rem;
      font-family: inherit;
      box-sizing: border-box;
      transition: all 0.2s;

      box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.15);

      &::placeholder {
        color: rgba(255, 255, 255, 0.3);
        font-size: 12px;
      }
    }
  }

  .tag-list-move,
  .tag-list-enter-active,
  .tag-list-leave-active {
    transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  }

  .tag-list-enter-from,
  .tag-list-leave-to {
    opacity: 0;
    transform: scale(0.8);
  }

  .tag-list-leave-active {
    position: absolute;
  }

  .tag-input-enter-active,
  .tag-input-leave-active {
    transition: all 0.2s ease;
  }

  .tag-input-enter-from,
  .tag-input-leave-to {
    opacity: 0;
    transform: scale(0.9);
  }
}

.exif-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
  padding-top: 0px;
}

.exif-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: rgba(255, 255, 255, 0.03);
  padding: 8px 10px;
  border-radius: 6px;
  overflow: hidden;

  border: 1px solid transparent;

  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.5, 1);
  cursor: pointer;
  user-select: none;

  .label {
    font-size: 0.7rem;
    color: var(--text-muted);
    transition: color 0.3s;
  }

  .value {
    font-size: 0.8rem;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.1);
    transform: scale(1.02);

    .label {
      color: var(--text-secondary);
    }

    .value {
      color: var(--text-main);
    }
  }

  &:active {
    transform: scale(0.96);
    background: rgba(255, 255, 255, 0.05);
    box-shadow: none;
  }
}

.file-meta-footer {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-align: center;
  margin-top: 40px;
}

.dock-confirm-btn {
  width: 36px;
  height: 36px;
  padding: 0 0px;
  border-radius: 50%;

  font-weight: 600;
  font-size: 14px;

  background-color: var(--primary-color) !important;
  border: none !important;
  color: var(--text-main) !important;
  transition: all 0.2s ease !important;

  :deep(span),
  :deep(.el-icon) {
    color: var(--text-main) !important;
    transition: color 0.2s ease;
  }

  &:hover {
    background-color: var(--primary-hover) !important;
    box-shadow: 0 0 10px rgba(var(--primary-color-rgb), 0.4);
  }

  &:active {
    opacity: 0.8;
  }
}
</style>

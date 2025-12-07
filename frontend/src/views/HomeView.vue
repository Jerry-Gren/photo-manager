<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { toast } from '@/utils/toast'
import LoadingButton from '@/components/LoadingButton.vue'
import AuthImg from '@/components/AuthImg.vue'
import { imageApi } from '@/api/image'
import type { ImageMeta } from '@/types'
import {
  Picture,
  Search,
  Upload,
  Setting,
  SwitchButton,
  Expand
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

/* State Management */
const isMobile = ref(false)
const showMobileMenu = ref(false)
const activeMenu = ref('gallery')
const searchQuery = ref('')
const isSearchFocused = ref(false)
const searchInputRef = ref<HTMLInputElement | null>(null)

/* Data State */
const images = ref<ImageMeta[]>([])
const loading = ref(false)
const hasMore = ref(true)
const skip = ref(0)
const limit = 20

/* Infinite Scroll */
const scrollContainer = ref<HTMLElement | null>(null)

/* Responsive Check */
const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    showMobileMenu.value = false
    isSearchFocused.value = false
  }
}

/**
 * Fetch Images from API
 * Handles pagination via skip/limit.
 * @param reset If true, clears the current list and starts from page 1.
 */
const fetchImages = async (reset = false) => {
  if (loading.value) return
  if (!reset && !hasMore.value) return

  loading.value = true
  if (reset) {
    images.value = []
    skip.value = 0
    hasMore.value = true
  }

  try {
    const res = await imageApi.getList({
      skip: skip.value,
      limit: limit,
      status: 'active',
      // Future: tags: searchQuery.value ? [searchQuery.value] : undefined
    })

    const newImages = res.data

    if (newImages.length < limit) {
      hasMore.value = false
    }

    images.value = [...images.value, ...newImages]
    skip.value += limit

  } catch (e) {
    console.error(e)
    toast.error('获取图片列表失败')
  } finally {
    loading.value = false
  }
}

/**
 * Infinite Scroll Handler
 * Triggers fetch when scrolling near the bottom.
 */
const handleScroll = (e: Event) => {
  const target = e.target as HTMLElement
  // Threshold: 100px from bottom
  if (target.scrollTop + target.clientHeight >= target.scrollHeight - 100) {
    fetchImages()
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  fetchImages(true)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const handleLogout = () => {
  userStore.logout()
  toast.success('已安全退出')
  router.push('/login')
}

const handleUpload = () => {
  toast.info('上传功能即将开启')
}

const toggleSearch = () => {
  if (!isMobile.value) return
  isSearchFocused.value = true
  nextTick(() => {
    searchInputRef.value?.focus()
  })
}

const handleSearchBlur = () => {
  if (!isMobile.value) return
  if (!searchQuery.value) {
    isSearchFocused.value = false
  }
}

/**
 * Helper: Determine the primary tag to display.
 * Priority: User Tag > AI Tag > Time/Location
 */
const getDisplayTag = (img: ImageMeta) => {
  const userTag = img.tags.find(t => t.tag_type === 'user')
  if (userTag) return userTag.name

  const aiTag = img.tags.find(t => t.tag_type === 'ai_generated')
  if (aiTag) return aiTag.name

  const timeTag = img.tags.find(t => t.tag_type === 'derived_time')
  return timeTag ? timeTag.name : 'Photo'
}

/**
 * Helper: Format location string.
 */
const getDisplayLocation = (img: ImageMeta) => {
  if (img.location_name) {
    return img.location_name
  }
  return 'Unknown Location'
}
</script>

<template>
  <div class="home-container">

    <header class="mobile-header" v-if="isMobile">
      <div class="logo-text">Photo<span class="highlight">Manager</span></div>
      <el-button link class="menu-btn" @click="showMobileMenu = true">
        <el-icon :size="24">
          <Expand />
        </el-icon>
      </el-button>
    </header>

    <div class="layout-wrapper" :class="{ 'is-mobile': isMobile }">

      <component :is="isMobile ? 'el-drawer' : 'aside'" v-model="showMobileMenu"
        :direction="isMobile ? 'ltr' : undefined" :size="isMobile ? '280px' : undefined" :with-header="false"
        class="sidebar-host" :class="{ 'premium-glass sidebar-desktop': !isMobile }">
        <div class="sidebar-inner">
          <div class="logo-area" v-if="!isMobile">
            <div class="logo-icon">P</div>
            <h2>Photo<span class="highlight">Manager</span></h2>
          </div>

          <div class="user-mini-card">
            <el-avatar :size="40" class="avatar-glow">{{ userStore.user?.username.charAt(0).toUpperCase() || 'U'
            }}</el-avatar>
            <div class="meta">
              <div class="name">{{ userStore.user?.username || 'Guest' }}</div>
              <div class="role">普通用户</div>
            </div>
          </div>

          <nav class="nav-menu">
            <div class="nav-group-title">MENU</div>
            <div class="nav-item" :class="{ active: activeMenu === 'gallery' }"
              @click="activeMenu = 'gallery'; showMobileMenu = false">
              <div class="icon-box"><el-icon>
                  <Picture />
                </el-icon></div>
              <span>我的图库</span>
            </div>
            <div class="nav-item" :class="{ active: activeMenu === 'smart-search' }"
              @click="activeMenu = 'smart-search'; showMobileMenu = false">
              <div class="icon-box"><el-icon>
                  <Search />
                </el-icon></div>
              <span>智能检索</span>
              <span class="badge">AI</span>
            </div>
          </nav>

          <div class="sidebar-footer">
            <div class="nav-item logout" @click="handleLogout">
              <el-icon>
                <SwitchButton />
              </el-icon>
              <span>退出登录</span>
            </div>
          </div>
        </div>
      </component>

      <main class="main-stage">
        <div class="content-panel premium-glass">
          <div class="ambient-light"></div>

          <div class="stage-header">

            <div class="search-capsule"
              :class="{ 'mobile-collapsed': isMobile && !isSearchFocused && !searchQuery, 'mobile-expanded': isMobile && isSearchFocused }"
              @click="toggleSearch">
              <el-icon class="search-icon">
                <Search />
              </el-icon>

              <input ref="searchInputRef" v-model="searchQuery" type="text" placeholder="Search..."
                @blur="handleSearchBlur" @keyup.enter="fetchImages(true)" />
              <div class="shortcut-hint" v-if="!isMobile">⌘K</div>
            </div>

            <div class="actions-group" :class="{ 'collapsed': isMobile && isSearchFocused }">
              <div class="tool-btn square" @click="fetchImages(true)">
                <el-icon>
                  <RefreshRight />
                </el-icon>
              </div>

              <div class="tool-btn square" @click="toast.info('设置')">
                <el-icon>
                  <Setting />
                </el-icon>
              </div>

              <LoadingButton class="tool-btn upload-btn" :class="{ 'square': isMobile }" @click="handleUpload">
                <el-icon :size="18">
                  <Upload />
                </el-icon>
                <span v-if="!isMobile" style="margin-left: 8px;">上传</span>
              </LoadingButton>
            </div>
          </div>

          <div ref="scrollContainer" class="stage-body custom-scroll" @scroll="handleScroll">
            <template v-if="activeMenu === 'gallery'">
              <div class="gallery-header">
                <h3>All Photos</h3>
                <div class="filter-tabs">
                  <span class="tab active">Timeline</span>
                  <span class="tab">Map</span>
                </div>
              </div>

              <div v-if="images.length === 0 && !loading" class="empty-state">
                <el-icon :size="48" color="#52525b">
                  <Picture />
                </el-icon>
                <p>暂无图片，快去上传吧</p>
              </div>

              <div class="gallery-grid">
                <div v-for="img in images" :key="img.id" class="photo-card"
                  @click="toast.info(`Clicked Image ${img.id}`)">
                  <div class="image-wrapper">
                    <AuthImg class="img" :src="imageApi.getThumbnailUrl(img.id)" :alt="img.original_filename" />

                    <div class="overlay"></div>
                    <div class="card-meta">
                      <div class="top-meta">
                        <span class="tag">{{ getDisplayTag(img) }}</span>
                      </div>
                      <div class="bottom-meta">
                        <div class="title" :title="img.title || img.original_filename">
                          {{ img.title || img.original_filename }}
                        </div>
                        <div class="loc" :title="getDisplayLocation(img)">
                          {{ getDisplayLocation(img) }}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="loading" class="loading-more">
                <el-icon class="is-loading">
                  <RefreshRight />
                </el-icon>
                <span>Loading more...</span>
              </div>
              <div v-if="!hasMore && images.length > 0" class="no-more">
                <span>已经到底啦</span>
              </div>
            </template>

            <template v-else-if="activeMenu === 'smart-search'">
              <div class="chat-placeholder">
                <h2>AI Smart Search</h2>
                <p>Chat interface coming soon...</p>
              </div>
            </template>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.home-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: rgba(15, 15, 17, 0.4);
  color: #fff;
  position: relative;
}

/* Premium Glass Effect */
.premium-glass {
  background: var(--bg-panel);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: none;
  box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.5);
  border-radius: 24px;
}

/* Layout */
.layout-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 24px;
  padding: 24px;
  position: relative;
  z-index: 1;

  &.is-mobile {
    padding: 16px;
    flex-direction: column;
  }
}

.mobile-header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;

  .logo-text {
    font-size: 1.25rem;
    font-weight: 800;

    .highlight {
      color: var(--primary-color);
    }
  }

  .menu-btn {
    color: var(--text-main);
  }
}

/* Sidebar */
.sidebar-host {
  height: 100%;
  flex-shrink: 0;
}

.sidebar-desktop {
  width: 260px;
  display: flex;
  flex-direction: column;
}

.sidebar-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    display: none;
  }
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 30px;
  flex-shrink: 0;

  .logo-icon {
    width: 32px;
    height: 32px;
    color: var(--text-main);
    background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 18px;
    box-shadow: 0 4px 12px rgba(249, 115, 22, 0.4);
  }

  h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-main);

    .highlight {
      color: var(--primary-color);
    }
  }
}

.user-mini-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  margin-bottom: 30px;
  flex-shrink: 0;

  .avatar-glow {
    background: #2c2c2c;
    color: var(--text-secondary);
    border: 1px solid var(--border-medium);
  }

  .meta {
    .name {
      font-weight: 600;
      color: var(--text-main);
      font-size: 0.9rem;
    }

    .role {
      font-size: 0.75rem;
      color: var(--primary-color);
      font-weight: 500;
    }
  }
}

.nav-menu {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 2px;

  &::-webkit-scrollbar {
    display: none;
  }

  .nav-group-title {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 8px;
    padding-left: 12px;
    margin-top: 10px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    cursor: pointer;
    color: var(--text-secondary);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    flex-shrink: 0;

    .icon-box {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.3s;
    }

    .badge {
      margin-left: auto;
      font-size: 0.65rem;
      background: var(--primary-light);
      color: var(--primary-color);
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 700;
    }

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-main);
    }

    &.active {
      background: linear-gradient(90deg, var(--primary-light), transparent);
      box-shadow: inset 2px 0 0 0 var(--primary-color);
      color: var(--text-main);

      .icon-box {
        color: var(--primary-color);
      }
    }
  }
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 20px;
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;

  .logout {
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
    }
  }
}

/* Main Stage */
.main-stage {
  flex: 1;
  height: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.content-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.ambient-light {
  position: absolute;
  top: -100px;
  left: 20%;
  width: 400px;
  height: 200px;
  background: var(--primary-color);
  filter: blur(120px);
  opacity: 0.15;
  pointer-events: none;
  z-index: 1;
}

/* Top Header */
.stage-header {
  height: 80px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  border-bottom: 1px solid var(--border-light);
  position: relative;
  z-index: 20;
}

@media (max-width: 768px) {
  .stage-header {
    padding: 0 16px;
  }
}

/* Search Capsule */
.search-capsule {
  position: relative;
  width: 100%;
  height: 40px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-medium);
  border-radius: 20px;
  display: block;
  transition:
    width 0.4s cubic-bezier(0.19, 1, 0.22, 1),
    border-radius 0.4s cubic-bezier(0.19, 1, 0.22, 1),
    background-color 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;

  &:focus-within {
    background: var(--bg-overlay);
    border-color: var(--el-color-primary);
    box-shadow: 0 0 0 1px var(--primary-color);
  }

  .search-icon {
    position: absolute;
    top: 0;
    left: 0;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    z-index: 10;
    transition: color 0.3s;
    pointer-events: none;
  }

  input {
    width: 100%;
    height: 100%;
    background: transparent;
    border: none;
    color: var(--text-main);
    font-size: 0.9rem;
    padding-left: 40px;
    padding-right: 40px;
    opacity: 1;
    transition: opacity 0.3s ease;

    &:focus {
      outline: none;
    }

    &::placeholder {
      color: var(--text-placeholder);
    }
  }

  .shortcut-hint {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.75rem;
    color: var(--text-placeholder);
    border: 1px solid var(--border-medium);
    padding: 2px 6px;
    border-radius: 4px;
    pointer-events: none;
  }

  &.mobile-collapsed {
    width: 40px;
    background: transparent;
    border-color: var(--border-light);
    border-radius: 12px;

    .search-icon {
      color: var(--text-secondary);
    }

    input {
      opacity: 0;
      pointer-events: none;
    }

    .shortcut-hint {
      display: none;
    }

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: var(--border-focus);
      color: var(--text-main);
    }
  }

  &.mobile-expanded {
    width: 100%;
    background: rgba(0, 0, 0, 0.6);
    border-color: var(--primary-color);

    .search-icon {
      color: var(--primary-color);
    }

    input {
      pointer-events: auto;
    }
  }
}

.actions-group {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 12px;
  flex-shrink: 0;
  overflow: hidden;
  max-width: 500px;
  opacity: 1;
  transform: translateX(0);
  transition:
    max-width 0.4s cubic-bezier(0.19, 1, 0.22, 1),
    opacity 0.3s ease,
    margin-left 0.4s ease,
    transform 0.4s ease;

  @media (max-width: 768px) {
    max-width: 160px;
  }

  .tool-btn {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    border-radius: 12px !important;
    border: 1px solid var(--border-light) !important;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    cursor: pointer;
    background: transparent !important;
    transition: all 0.2s ease;
    position: relative;

    &.upload-btn {
      width: auto;
      padding: 0 20px;
      white-space: nowrap;

      &.square {
        width: 40px;
        padding: 0;
      }
    }

    &:hover {
      background: rgba(255, 255, 255, 0.1) !important;
      color: var(--text-main);
      border-color: var(--border-focus) !important;
    }

    &:active {
      background: rgba(255, 255, 255, 0.05) !important;
    }

    .dot {
      position: absolute;
      top: 10px;
      right: 10px;
      width: 6px;
      height: 6px;
      background: #ef4444;
      border-radius: 50%;
      border: 1px solid #202023;
    }

    :deep(span) {
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }

  &.collapsed {
    max-width: 0;
    opacity: 0;
    gap: 0;
    margin-left: 0;
    transform: translateX(20px);
    pointer-events: none;
  }
}

/* Body */
.stage-body {
  flex: 1;
  overflow-y: auto;
  padding: 30px;
  min-height: 0;
  position: relative;
  z-index: 20;
}

/* Gallery Header */
.gallery-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 20px;
  row-gap: 16px;

  h3 {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
    white-space: nowrap;
    color: var(--text-main);
  }

  .filter-tabs {
    display: flex;
    background: rgba(0, 0, 0, 0.2);
    padding: 4px;
    border-radius: 10px;
    flex-shrink: 0;

    .tab {
      padding: 6px 16px;
      font-size: 0.85rem;
      border-radius: 8px;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;

      &.active {
        background: rgba(255, 255, 255, 0.1);
        color: var(--text-main);
        font-weight: 600;
      }

      &:hover:not(.active) {
        color: #d4d4d8;
      }
    }
  }
}

@media (max-width: 768px) {
  .stage-body {
    padding: 20px;
  }

  .gallery-header {
    h3 {
      width: 100%;
    }

    .filter-tabs {
      width: 100%;
      justify-content: space-between;
    }

    .tab {
      flex: 1;
      text-align: center;
    }
  }
}

/* Grid */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
  padding-bottom: 40px;
}

.photo-card {
  position: relative;
  aspect-ratio: 3/4;
  border-radius: 16px;
  cursor: pointer;
  transition: transform 0.4s cubic-bezier(0.2, 0, 0.2, 1), box-shadow 0.4s ease;

  &:hover {
    transform: translateY(-8px) scale(1.02);
    z-index: 30;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);

    .overlay {
      opacity: 1;
    }

    .card-meta {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .image-wrapper {
    width: 100%;
    height: 100%;
    border-radius: 16px;
    overflow: hidden;
    position: relative;
    background: #18181b;
  }

  .img {
    width: 100%;
    height: 100%;
    background-size: cover;
    background-position: center;
    transition: transform 0.5s;
  }

  .overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0, 0, 0, 0.9), transparent 60%);
    opacity: 0;
    transition: opacity 0.3s;
  }

  .card-meta {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    padding: 20px;
    box-sizing: border-box;
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    height: 100%;
    overflow: hidden;

    .top-meta {
      margin-bottom: auto;
      display: flex;
      justify-content: flex-end;

      .tag {
        margin-top: 0px;
        margin-right: 0px;
        background: rgba(0, 0, 0, 0.7);
        color: #fbfbfb;
        backdrop-filter: blur(4px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        font-size: 10px;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 700;
        text-transform: uppercase;
        max-width: 120px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .bottom-meta {
      width: 100%;
      display: flex;
      flex-direction: column;
    }

    .title {
      color: var(--text-main);
      font-weight: 600;
      font-size: 1rem;
      margin-bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      width: 100%;
      display: block;
    }

    .loc {
      color: rgba(255, 255, 255, 0.6);
      font-size: 0.8rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      width: 100%;
      display: block;
    }
  }
}

@media (max-width: 768px) {
  .gallery-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .photo-card .card-meta {
    padding: 12px;
  }

  .photo-card .title {
    font-size: 0.9rem;
  }
}

.custom-scroll::-webkit-scrollbar {
  width: 6px;
}

.custom-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scroll::-webkit-scrollbar-thumb {
  background: var(--border-medium);
  border-radius: 3px;
}

:deep(.el-drawer) {
  background: var(--bg-color) !important;

  .el-drawer__body {
    padding: 0;
  }
}

/* Helpers */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: var(--text-muted);

  p {
    margin-top: 16px;
    font-size: 0.9rem;
  }
}

.loading-more,
.no-more {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
  color: var(--text-placeholder);
  font-size: 0.85rem;
  gap: 8px;
}

.photo-card :deep(.auth-img-container) {
  width: 100%;
  height: 100%;
}

.chat-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}
</style>

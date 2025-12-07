import http from '@/utils/http'
import type { ImageMeta, ImageSearchParams } from '@/types'

export const imageApi = {
  getList: (params: ImageSearchParams) => {
    const queryParams = new URLSearchParams()
    if (params.skip !== undefined) queryParams.append('skip', params.skip.toString())
    if (params.limit !== undefined) queryParams.append('limit', params.limit.toString())
    if (params.status) queryParams.append('status', params.status)
    if (params.sort_by) queryParams.append('sort_by', params.sort_by)
    if (params.sort_order) queryParams.append('sort_order', params.sort_order)

    if (params.tags) {
      params.tags.forEach(tag => queryParams.append('tags', tag))
    }

    return http.get<ImageMeta[]>(`/images?${queryParams.toString()}`)
  },

  getDetail: (id: number) => {
    return http.get<ImageMeta>(`/images/${id}`)
  },

  getThumbnailUrl: (id: number) => `/images/${id}/thumbnail`,

  getOriginalUrl: (id: number) => `/images/${id}/file`,

  delete: (id: number) => http.delete(`/images/${id}`),

  removeTag: (imageId: number, tagId: number) => http.delete(`/images/${imageId}/tags/${tagId}`),

  addTag: (imageId: number, tagName: string) => http.post(`/images/${imageId}/tags`, { name: tagName })
}

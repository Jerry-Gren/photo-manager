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
    if (params.start_date) queryParams.append('start_date', params.start_date)
    if (params.end_date) queryParams.append('end_date', params.end_date)
    if (params.q) queryParams.append('q', params.q)
    if (params.date_field) queryParams.append('date_field', params.date_field)

    if (params.tags) {
      params.tags.forEach(tag => queryParams.append('tags', tag))
    }

    return http.get<ImageMeta[]>(`/images?${queryParams.toString()}`)
  },

  getDetail: (id: number) => {
    return http.get<ImageMeta>(`/images/${id}`)
  },

  upload: (file: File, title?: string, description?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (title) formData.append('title', title)
    if (description) formData.append('description', description)

    return http.post<ImageMeta>('/images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  edit: (
    id: number,
    payload: {
      crop?: { x: number; y: number; width: number; height: number };
      filter?: string
    }
  ) => {
    return http.post<ImageMeta>(`/images/${id}/edit`, payload)
  },

  getThumbnailUrl: (id: number) => `/images/${id}/thumbnail`,

  getOriginalUrl: (id: number) => `/images/${id}/file`,

  delete: (id: number) => http.delete(`/images/${id}`),

  removeTag: (imageId: number, tagId: number) => http.delete(`/images/${imageId}/tags/${tagId}`),

  addTag: (imageId: number, tagName: string) => http.post(`/images/${imageId}/tags`, { name: tagName })
}

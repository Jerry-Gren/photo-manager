export type JSONValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JSONValue }
  | JSONValue[]

export interface Tag {
  id: number
  name: string
  tag_type: string // 'user', 'derived_time', 'exif_location', 'ai_generated'
}

export interface AIAnalysisData {
  caption: string
  tags: string[]
  location_zh?: string
}

export interface ImageMeta {
  id: number
  user_id: number
  original_filename: string
  mime_type: string
  file_size: number
  status: 'processing' | 'active' | 'archived' | 'failed' | 'active_deleted'
  processing_error?: string | null
  uploaded_at: string

  // Custom Meta
  title?: string
  description?: string

  // Derived
  taken_at?: string
  location_name?: string
  resolution_width?: number
  resolution_height?: number

  ai_analysis?: AIAnalysisData | null
  exif_data?: Record<string, JSONValue> | null

  tags: Tag[]

  // UI Helper (frontend only)
  thumbnailUrl?: string
}

export interface ImageSearchParams {
  skip?: number
  limit?: number
  q?: string
  tags?: string[]
  status?: string
  date_field?: 'taken_at' | 'uploaded_at'
  start_date?: string
  end_date?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

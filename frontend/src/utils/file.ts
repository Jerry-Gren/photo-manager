export const ACCEPT_EXTENSIONS = [
  'image/jpeg', 'image/png', 'image/gif', 'image/webp', // Web Safe
  'image/heic', 'image/heif', // HEIC
  'image/tiff', 'image/bmp',  // Other Bitmap
  'image/jxl', 'image/avif',
  '.nef', '.cr2', '.dng', '.arw', '.orf', '.rw2', '.pef', '.sr2', '.cr3' // RAW
].join(',')

export const WEB_SAFE_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/svg+xml'
]

export const isWebSafeImage = (mimeType: string): boolean => {
  if (!mimeType) return false

  const baseType = (mimeType.split(';')[0] ?? '').toLowerCase().trim()

  return WEB_SAFE_MIME_TYPES.includes(baseType)
}

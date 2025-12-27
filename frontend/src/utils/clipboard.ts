/**
 * Utilities for clipboard operations.
 * Handles cross-browser compatibility and non-secure context fallbacks.
 */

/**
 * Copies text to the system clipboard.
 * Strategy:
 * 1. Tries to use the modern `navigator.clipboard.writeText` API (requires Secure Context: HTTPS or localhost).
 * 2. Fallback to `document.execCommand('copy')` using a temporary textarea for non-secure contexts (e.g., HTTP on LAN IP).
 * @param text The string to copy.
 * @returns A Promise that resolves when the copy is successful, or rejects if it fails.
 */
export async function copyToClipboard(text: string): Promise<void> {
  if (!text) return Promise.reject('No text to copy')

  // Strategy 1: Modern API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return Promise.resolve()
    } catch (error) {
      console.warn('Clipboard API failed, trying fallback...', error)
    }
  }

  // Strategy 2: Legacy Fallback
  return new Promise((resolve, reject) => {
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text

      // Ensure the element is not visible but part of the DOM
      textArea.style.position = 'fixed'
      textArea.style.left = '-9999px'
      textArea.style.top = '0'
      document.body.appendChild(textArea)

      textArea.focus()
      textArea.select()

      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)

      if (successful) {
        resolve()
      } else {
        reject(new Error('Fallback: execCommand returned false'))
      }
    } catch (err) {
      reject(err)
    }
  })
}

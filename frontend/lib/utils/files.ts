// ═══════════════════════════════════════════════════════════════════════════
// File Utilities
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Determine file type from filename extension
 */
export function getFileType(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  
  const typeMap: Record<string, string> = {
    'py': 'python',
    'md': 'markdown',
    'csv': 'csv',
    'json': 'json',
    'html': 'html',
    'js': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'jsx': 'javascript',
    'css': 'css',
    'scss': 'scss',
    'sql': 'sql',
    'sh': 'bash',
    'bash': 'bash',
    'yaml': 'yaml',
    'yml': 'yaml',
    'xml': 'xml',
    'txt': 'text',
  };
  
  return typeMap[ext || ''] || 'text';
}

/**
 * Check if a filename represents an image file
 */
export function isImageFile(filename: string): boolean {
  return /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(filename);
}

/**
 * Check if a filename represents a binary image file (not SVG)
 */
export function isBinaryImageFile(filename: string): boolean {
  return /\.(png|jpg|jpeg|gif|webp)$/i.test(filename);
}

/**
 * Check if a filename represents a CSV file
 */
export function isCsvFile(filename: string): boolean {
  return /\.csv$/i.test(filename);
}

/**
 * Check if a filename represents an HTML file
 */
export function isHtmlFile(filename: string): boolean {
  return /\.html$/i.test(filename);
}

/**
 * Get the API base URL
 */
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

/**
 * Build a chat file download URL
 */
export function getChatFileUrl(chatId: string, filename: string): string {
  return `${getApiBaseUrl()}/api/chat-files/${chatId}/download/${encodeURIComponent(filename)}`;
}

/**
 * Fetch a file and convert to base64 (for images)
 */
export async function fetchFileAsBase64(url: string): Promise<string> {
  const response = await fetch(url);
  const blob = await response.blob();
  
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      const base64Data = base64.split(',')[1] || base64;
      resolve(base64Data);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Fetch file content (text or base64 for images)
 */
export async function fetchFileContent(
  chatId: string,
  filename: string
): Promise<{ content: string; fileType: string }> {
  const url = getChatFileUrl(chatId, filename);
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch file: ${response.status}`);
  }
  
  const fileType = filename.split('.').pop()?.toLowerCase() || 'text';
  
  if (isImageFile(filename)) {
    const content = await fetchFileAsBase64(url);
    return { content, fileType };
  }
  
  const content = await response.text();
  return { content, fileType };
}


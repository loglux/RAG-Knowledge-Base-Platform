import React, { useCallback, useState } from 'react'

interface FileUploadProps {
  onUpload: (files: File[]) => Promise<void>
  accept?: string
  maxSize?: number // in MB
  multiple?: boolean
}

export function FileUpload({
  onUpload,
  accept = '.txt,.md',
  maxSize = 50,
  multiple = true,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const validateFiles = (files: File[]): { valid: File[]; errors: string[] } => {
    const valid: File[] = []
    const errors: string[] = []
    const maxBytes = maxSize * 1024 * 1024

    for (const file of files) {
      // Check file size
      if (file.size > maxBytes) {
        errors.push(`${file.name}: File too large (max ${maxSize}MB)`)
        continue
      }

      // Check file type
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      const acceptedTypes = accept.split(',').map((t) => t.trim().toLowerCase())

      if (!acceptedTypes.includes(ext)) {
        errors.push(`${file.name}: File type not supported`)
        continue
      }

      valid.push(file)
    }

    return { valid, errors }
  }

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const fileArray = Array.from(files)
    const { valid, errors } = validateFiles(fileArray)

    if (errors.length > 0) {
      alert(errors.join('\n'))
    }

    if (valid.length === 0) return

    setIsUploading(true)
    try {
      await onUpload(valid)
    } catch (error) {
      console.error('Upload failed:', error)
      alert(error instanceof Error ? error.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      await handleFiles(e.dataTransfer.files)
    },
    [onUpload]
  )

  const handleFileInput = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      await handleFiles(e.target.files)
      // Reset input so same file can be selected again
      e.target.value = ''
    },
    [onUpload]
  )

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center transition-colors
        ${isDragging ? 'border-primary-500 bg-primary-500 bg-opacity-10' : 'border-gray-600 bg-gray-800'}
        ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-primary-500'}
      `}
    >
      <input
        type="file"
        id="file-upload"
        className="hidden"
        accept={accept}
        multiple={multiple}
        onChange={handleFileInput}
        disabled={isUploading}
      />

      <label
        htmlFor="file-upload"
        className={`cursor-pointer ${isUploading ? 'cursor-not-allowed' : ''}`}
      >
        <div className="flex flex-col items-center space-y-3">
          <div className="text-4xl">
            {isUploading ? '⏳' : isDragging ? '📥' : '📁'}
          </div>

          <div className="text-lg font-medium text-white">
            {isUploading
              ? 'Uploading...'
              : isDragging
              ? 'Drop files here'
              : 'Drag & Drop files here'}
          </div>

          <div className="text-sm text-gray-400">
            or click to browse
          </div>

          <div className="text-xs text-gray-500 mt-2">
            <div>Supported: {accept.replace(/\./g, '').toUpperCase()}</div>
            <div>Max size: {maxSize} MB</div>
          </div>
        </div>
      </label>
    </div>
  )
}

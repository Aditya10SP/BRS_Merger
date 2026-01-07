import React from 'react'
import { X, FileText } from 'lucide-react'
import { FileData } from '../types'

interface FileListProps {
  files: FileData[]
  onRemove: (index: number) => void
}

const FileList: React.FC<FileListProps> = ({ files, onRemove }) => {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="space-y-3">
      {files.map((fileData, index) => (
        <div
          key={index}
          className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-center space-x-3 flex-1 min-w-0">
            <div className="bg-primary/10 p-2 rounded-lg flex-shrink-0">
              <FileText className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-secondary truncate">
                {fileData.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(fileData.size)}
              </p>
            </div>
          </div>
          <button
            onClick={() => onRemove(index)}
            className="ml-4 p-2 text-muted-foreground hover:text-destructive hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
            aria-label="Remove file"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      ))}
    </div>
  )
}

export default FileList


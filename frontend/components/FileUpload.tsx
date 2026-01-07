import React, { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText } from 'lucide-react'
import { FileData } from '../types'

interface FileUploadProps {
  onFilesSelected: (files: FileData[]) => void
  disabled?: boolean
}

const FileUpload: React.FC<FileUploadProps> = ({ onFilesSelected, disabled }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const fileData: FileData[] = acceptedFiles.map(file => ({
      file,
      name: file.name,
      size: file.size,
      type: file.type,
    }))
    onFilesSelected(fileData)
  }, [onFilesSelected])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt']
    },
    disabled,
    multiple: true
  })

  return (
    <div>
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive 
            ? 'border-primary bg-primary/5 scale-105' 
            : 'border-gray-300 hover:border-primary hover:bg-gray-50'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className={`
            p-4 rounded-full
            ${isDragActive ? 'bg-primary text-white' : 'bg-primary/10 text-primary'}
            transition-all duration-200
          `}>
            <Upload className="w-8 h-8" />
          </div>
          
          {isDragActive ? (
            <p className="text-lg font-semibold text-primary">
              Drop your BRS/CR documents here...
            </p>
          ) : (
            <>
              <div>
                <p className="text-lg font-semibold text-secondary mb-2">
                  Drag & drop your BRS versions and CRs here
                </p>
                <p className="text-sm text-muted-foreground">
                  or click to browse files
                </p>
              </div>
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <FileText className="w-4 h-4" />
                <span>PDF, DOCX, or TXT files</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default FileUpload

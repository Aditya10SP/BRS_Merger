import React, { useState } from 'react'
import { Merge } from 'lucide-react'
import axios from 'axios'
import { FileData } from '../types'

interface MergeButtonProps {
  files: FileData[]
  useRAG: boolean
  onMergeStart: () => void
  onMergeComplete: (result: { downloadUrl: string; mergedText: string }) => void
  onMergeError?: () => void
  disabled?: boolean
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const MergeButton: React.FC<MergeButtonProps> = ({
  files,
  useRAG,
  onMergeStart,
  onMergeComplete,
  onMergeError,
  disabled
}) => {
  const [error, setError] = useState<string | null>(null)

  const handleMerge = async () => {
    if (files.length === 0) return

    try {
      setError(null)
      onMergeStart()

      // Create FormData
      const formData = new FormData()
      files.forEach((fileData) => {
        formData.append('files', fileData.file)
      })

      // Call API - upload and merge in one step
      const response = await axios.post(
        `${API_BASE_URL}/api/upload-and-merge`,
        formData,
        {
          params: {
            use_rag: useRAG,
            output_filename: 'merged_brs.pdf'
          },
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 600000, // 10 minute timeout for AI processing (large batches can take time)
        }
      )

      // Create download URL for the merged document
      const filename = response.data.output_path || 'merged_brs.pdf'
      const downloadUrl = `${API_BASE_URL}/api/download/${filename}`
      
      onMergeComplete({
        downloadUrl,
        mergedText: response.data.merged_document || ''
      })
    } catch (err: any) {
      console.error('Merge error:', err)
      
      let errorMessage = 'Failed to merge documents. Please try again.'
      
      if (err.code === 'ECONNREFUSED' || err.message?.includes('Network Error') || !err.response) {
        errorMessage = 'Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000'
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
      if (onMergeError) {
        onMergeError()
      }
    }
  }

  return (
    <div className="w-full max-w-md">
      <button
        onClick={handleMerge}
        disabled={disabled || files.length === 0}
        className={`
          icici-button w-full flex items-center justify-center space-x-2
          ${disabled || files.length === 0 
            ? 'opacity-50 cursor-not-allowed' 
            : ''
          }
        `}
      >
        <Merge className="w-5 h-5" />
        <span>Merge {files.length} Document{files.length !== 1 ? 's' : ''} with AI</span>
      </button>
      
          {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800 font-medium mb-1">Error:</p>
          <p className="text-sm text-red-700">{error}</p>
          {error.includes('Cannot connect') && (
            <div className="text-xs text-red-600 mt-2 space-y-1">
              <p>• Check if backend server is running: <code className="bg-red-100 px-1 rounded">cd backend && python main.py</code></p>
              <p>• Verify backend is accessible at: <code className="bg-red-100 px-1 rounded">http://localhost:8000</code></p>
              <p>• Check browser console for detailed error messages</p>
            </div>
          )}
          {error.includes('timeout') && (
            <p className="text-xs text-red-600 mt-2">
              Processing is taking longer than expected. For large batches (9+ documents), this can take 5-10 minutes. Please try again or reduce the number of documents.
            </p>
          )}
          {error.includes('Ollama') && (
            <p className="text-xs text-red-600 mt-2">
              Make sure Ollama is running and the model is installed. Run: ollama pull llama3.2
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default MergeButton

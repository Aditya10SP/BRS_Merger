export interface FileData {
  file: File
  name: string
  size: number
  type: string
}

export interface MergeResponse {
  success: boolean
  message: string
  output_path?: string
  file_paths?: string[]
}


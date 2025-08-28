'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'

export function VeoUploader() {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const handleVeoUpload = useCallback(async (file: File) => {
    setUploading(true)
    setError(null)
    
    try {
      // For large VEO files, use chunked upload
      const chunkSize = 50 * 1024 * 1024 // 50MB chunks
      const totalChunks = Math.ceil(file.size / chunkSize)
      
      // Create FormData with file info
      const initData = new FormData()
      initData.append('filename', file.name)
      initData.append('file_size', file.size.toString())
      initData.append('total_chunks', totalChunks.toString())
      
      // Initialize upload session
      const { data: session } = await axios.post(
        `${API_URL}/api/videos/upload/init`,
        initData
      )
      
      const { session_id: sessionId, video_id: videoId } = session
      
      // Upload chunks
      for (let i = 0; i < totalChunks; i++) {
        const start = i * chunkSize
        const end = Math.min(start + chunkSize, file.size)
        const chunk = file.slice(start, end)
        
        const chunkData = new FormData()
        chunkData.append('chunk', chunk)
        chunkData.append('chunk_index', i.toString())
        chunkData.append('session_id', sessionId)
        
        await axios.post(
          `${API_URL}/api/videos/upload/chunk`,
          chunkData,
          {
            onUploadProgress: (progressEvent) => {
              if (progressEvent.total) {
                const chunkProgress = (progressEvent.loaded / progressEvent.total) * 100
                const totalProgress = ((i + chunkProgress / 100) / totalChunks) * 100
                setProgress(Math.round(totalProgress))
              }
            }
          }
        )
      }
      
      // Complete upload
      const completeData = new FormData()
      completeData.append('session_id', sessionId)
      
      await axios.post(
        `${API_URL}/api/videos/upload/complete`,
        completeData
      )
      
      // Navigate to video page
      router.push(`/games/${videoId}`)
      
    } catch (err) {
      console.error('Upload failed:', err)
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }, [router, API_URL])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file type
      const validTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska']
      if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|mov|avi|mkv)$/i)) {
        setError('Please select a valid video file (MP4, MOV, AVI, or MKV)')
        return
      }
      
      // Check file size (max 5GB)
      if (file.size > 5 * 1024 * 1024 * 1024) {
        setError('File is too large (maximum 5GB)')
        return
      }
      
      handleVeoUpload(file)
    }
  }

  return (
    <div className="p-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold mb-4 text-white">Upload VEO 3 Recording</h2>
        
        <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 bg-gray-800">
          <input
            type="file"
            accept="video/*"
            onChange={handleFileSelect}
            className="hidden"
            id="veo-upload"
            disabled={uploading}
          />
          
          <label
            htmlFor="veo-upload"
            className={`cursor-pointer flex flex-col items-center ${
              uploading ? 'cursor-not-allowed' : ''
            }`}
          >
            {uploading ? (
              <>
                <div className="w-full bg-gray-700 rounded-full h-4 mb-4">
                  <div 
                    className="bg-blue-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-white">Uploading... {progress}%</p>
                <p className="text-sm text-gray-400 mt-2">
                  This may take several minutes for large files
                </p>
              </>
            ) : (
              <>
                <svg 
                  className="w-16 h-16 text-gray-400 mb-4" 
                  fill="none" 
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" 
                  />
                </svg>
                <p className="text-lg text-white">Click to upload VEO 3 recording</p>
                <p className="text-sm text-gray-400 mt-2">Supports files up to 5GB</p>
              </>
            )}
          </label>
        </div>
        
        {error && (
          <div className="mt-4 p-3 bg-red-900/20 border border-red-500 rounded-lg">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}
        
        <div className="mt-4 text-sm text-gray-400">
          <p className="font-semibold mb-2">The system will automatically:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Convert video for optimal streaming</li>
            <li>Create multiple quality levels (1080p, 720p, 480p)</li>
            <li>Generate HLS segments for smooth playback</li>
            <li>Process in background (you&apos;ll be notified when ready)</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
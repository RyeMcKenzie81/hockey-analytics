'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import axios from 'axios'
import { VideoPlayer } from '@/components/VideoPlayer'
import { useWebSocket } from '@/hooks/useWebSocket'

interface VideoData {
  id: string
  filename: string
  status: 'uploading' | 'processing' | 'ready' | 'error'
  metadata?: {
    duration: number
    fps: number
    resolution: string
    hls_manifest?: string
  }
  error?: string
}

export default function GamePage() {
  const params = useParams()
  const videoId = params.id as string
  const [video, setVideo] = useState<VideoData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  
  // WebSocket connection for real-time updates
  const { lastMessage, isConnected } = useWebSocket(videoId, {
    onMessage: (message) => {
      if (message.type === 'status' && message.status) {
        setVideo(prev => prev ? { ...prev, status: message.status as VideoData['status'] } : null)
      }
      if (message.type === 'ready') {
        // Reload video data when processing is complete
        fetchVideo()
      }
    }
  })
  
  const fetchVideo = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/videos/${videoId}`)
      setVideo(response.data)
    } catch (err) {
      console.error('Failed to fetch video:', err)
      setError('Failed to load video')
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    fetchVideo()
  }, [videoId])
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white">Loading video...</div>
      </div>
    )
  }
  
  if (error || !video) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-red-500">{error || 'Video not found'}</div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">{video.filename}</h1>
          <div className="flex items-center gap-4">
            <span className={`px-3 py-1 rounded-full text-sm ${
              video.status === 'ready' ? 'bg-green-600' :
              video.status === 'processing' ? 'bg-yellow-600' :
              video.status === 'error' ? 'bg-red-600' :
              'bg-gray-600'
            }`}>
              {video.status}
            </span>
            {isConnected && (
              <span className="text-green-400 text-sm">● Live Updates</span>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            {video.status === 'ready' && video.metadata?.hls_manifest ? (
              <VideoPlayer 
                videoId={video.id}
                className="w-full rounded-lg"
                onTimeUpdate={(time) => console.log('Current time:', time)}
                onError={(error) => setError(error)}
              />
            ) : video.status === 'processing' ? (
              <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                  <p className="text-gray-400">Video is being processed...</p>
                  <p className="text-sm text-gray-500 mt-2">This may take a few minutes</p>
                </div>
              </div>
            ) : video.status === 'error' ? (
              <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <p className="text-red-400">Failed to process video</p>
                  <p className="text-sm text-gray-500 mt-2">{video.error || 'Unknown error occurred'}</p>
                </div>
              </div>
            ) : (
              <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
                <p className="text-gray-400">Uploading...</p>
              </div>
            )}
          </div>
          
          <div className="lg:col-span-1">
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Video Information</h2>
              
              {video.metadata && (
                <dl className="space-y-3">
                  <div>
                    <dt className="text-sm text-gray-400">Duration</dt>
                    <dd className="text-lg">{Math.floor(video.metadata.duration / 60)}:{String(Math.floor(video.metadata.duration % 60)).padStart(2, '0')}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-400">Resolution</dt>
                    <dd className="text-lg">{video.metadata.resolution}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-400">Frame Rate</dt>
                    <dd className="text-lg">{video.metadata.fps.toFixed(2)} fps</dd>
                  </div>
                </dl>
              )}
              
              {!video.metadata && video.status === 'processing' && (
                <p className="text-gray-400 text-sm">
                  Video information will appear here once processing is complete.
                </p>
              )}
            </div>
            
            {lastMessage && (
              <div className="bg-gray-800 rounded-lg p-6 mt-4">
                <h3 className="text-sm font-semibold mb-2 text-gray-400">Latest Update</h3>
                <pre className="text-xs text-gray-300 overflow-auto">
                  {JSON.stringify(lastMessage, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
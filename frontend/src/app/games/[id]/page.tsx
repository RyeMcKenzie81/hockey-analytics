'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { useParams } from 'next/navigation'
import axios from 'axios'
import { VideoPlayer } from '@/components/VideoPlayer'
import { EventTimeline } from '@/components/EventTimeline'
import { EventList } from '@/components/EventList'
import { StatsPanel } from '@/components/StatsPanel'
import { useWebSocket } from '@/hooks/useWebSocket'

interface VideoData {
  id: string
  filename: string
  status: 'uploading' | 'processing' | 'processed' | 'failed'
  metadata?: {
    duration: number
    fps: number
    resolution: string
    hls_manifest?: string
    processing_progress?: number
    processing_stage?: string
    processing_quality?: string
  }
  error?: string
}

interface Event {
  id: string
  timestamp_seconds: number
  event_type: string
  confidence_score: number
  verified?: boolean
  detection_method?: string
  metadata?: Record<string, unknown>
  frame_data?: Record<string, unknown>
}

export default function GamePage() {
  const params = useParams()
  const videoId = params.id as string
  const videoRef = useRef<HTMLVideoElement>(null)
  const [video, setVideo] = useState<VideoData | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [currentTime, setCurrentTime] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [shouldConnectWS, setShouldConnectWS] = useState(false)
  const [mlProcessing, setMlProcessing] = useState(false)
  
  // Track current time in a ref to prevent re-renders
  const currentTimeRef = useRef(0)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  
  // WebSocket connection for real-time updates - only connect if video is processing
  const { isConnected } = useWebSocket(shouldConnectWS ? videoId : '', {
    onMessage: (message) => {
      if (message.type === 'status' && message.status) {
        setVideo(prev => {
          if (!prev) return null
          
          // Create updated video object
          const updated: VideoData = {
            ...prev,
            status: message.status as VideoData['status']
          }
          
          // Update metadata if provided
          if (message.metadata && prev.metadata) {
            updated.metadata = {
              ...prev.metadata,
              ...message.metadata
            } as VideoData['metadata']
          }
          
          // Only return updated if something changed
          if (prev.status !== updated.status || 
              JSON.stringify(prev.metadata) !== JSON.stringify(updated.metadata)) {
            return updated
          }
          
          return prev
        })
      }
      if (message.type === 'ready' || message.type === 'error') {
        // Disconnect WebSocket after processing is done
        setShouldConnectWS(false)
      }
    }
  })
  
  const fetchVideo = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/videos/${videoId}`)
      
      // Only update state if something actually changed
      setVideo(prev => {
        // If status or metadata changed, update
        if (!prev || prev.status !== response.data.status || 
            JSON.stringify(prev.metadata) !== JSON.stringify(response.data.metadata)) {
          return response.data
        }
        return prev  // No changes, keep existing state
      })
      
      // Only connect WebSocket if video is still processing (and not already connected)
      if ((response.data.status === 'uploading' || response.data.status === 'processing') && !shouldConnectWS) {
        setShouldConnectWS(true)
      } else if (response.data.status === 'processed' || response.data.status === 'failed') {
        setShouldConnectWS(false)
      }
      
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch video:', err)
      setError('Failed to load video')
      setLoading(false)
    }
  }
  
  const jumpToEvent = (event: Event) => {
    if (videoRef.current) {
      videoRef.current.currentTime = event.timestamp_seconds
    }
  }
  
  // Memoized time update handler that uses requestAnimationFrame for throttling
  const handleTimeUpdate = useMemo(() => {
    let animationFrameId: number | null = null
    let lastUpdateTime = 0
    
    return (time: number) => {
      currentTimeRef.current = time
      
      // Cancel any pending animation frame
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId)
      }
      
      // Only update state at most every 250ms to prevent excessive re-renders
      const now = Date.now()
      if (now - lastUpdateTime > 250) {
        lastUpdateTime = now
        animationFrameId = requestAnimationFrame(() => {
          setCurrentTime(time)
          animationFrameId = null
        })
      }
    }
  }, [])
  
  // Memoized error handler to prevent re-renders
  const handleVideoError = useMemo(() => {
    return (errorMessage: string) => {
      setError(errorMessage)
    }
  }, [])

  const verifyEvent = async (eventId: string, verified: boolean) => {
    // Update local state
    setEvents(prevEvents => 
      prevEvents.map(e => 
        e.id === eventId ? { ...e, verified } : e
      )
    )
    
    // Send verification to backend
    try {
      await axios.post(`${API_URL}/api/ml/events/verify/${eventId}`, null, {
        params: { verified }
      })
    } catch (err) {
      console.error('Failed to verify event:', err)
    }
  }
  
  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/ml/events/${videoId}`)
      setEvents(response.data)
    } catch (err) {
      console.error('Failed to fetch events:', err)
    }
  }
  
  const startMLProcessing = async () => {
    if (mlProcessing || !video || video.status !== 'processed') return
    
    setMlProcessing(true)
    try {
      const response = await axios.post(`${API_URL}/api/ml/process`, {
        video_id: videoId,
        org_id: 'default', // Use default org for now
        use_gemini: true
      })
      
      // Start polling for ML results
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get(`${API_URL}/api/ml/status/${response.data.processing_id}`)
          
          if (statusResponse.data.status === 'completed') {
            clearInterval(pollInterval)
            setMlProcessing(false)
            await fetchEvents() // Refresh events
          } else if (statusResponse.data.status === 'failed') {
            clearInterval(pollInterval)
            setMlProcessing(false)
            setError('ML processing failed')
          }
        } catch (err) {
          console.error('Failed to check ML status:', err)
        }
      }, 3000)
      
      // Stop polling after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        setMlProcessing(false)
      }, 5 * 60 * 1000)
      
    } catch (err) {
      console.error('Failed to start ML processing:', err)
      setMlProcessing(false)
      setError('Failed to start ML processing')
    }
  }

  useEffect(() => {
    // Initial fetch only
    fetchVideo()
  }, [videoId]) // eslint-disable-line react-hooks/exhaustive-deps
  
  // Poll for updates when video is processing
  useEffect(() => {
    if (video?.status === 'processing' || video?.status === 'uploading') {
      const interval = setInterval(() => {
        fetchVideo()
      }, 3000) // Poll every 3 seconds
      
      return () => clearInterval(interval)
    }
  }, [video?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch real events when video is processed
  useEffect(() => {
    if (video?.status === 'processed') {
      fetchEvents()
    }
  }, [video?.status]) // eslint-disable-line react-hooks/exhaustive-deps
  
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
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
            <span className={`px-3 py-1 rounded-full text-sm ${
              video.status === 'processed' ? 'bg-green-600' :
              video.status === 'processing' ? 'bg-yellow-600' :
              video.status === 'failed' ? 'bg-red-600' :
              'bg-gray-600'
            }`}>
              {video.status}
            </span>
            {isConnected && (
              <span className="text-green-400 text-sm">● Live Updates</span>
            )}
            </div>
            {video.status === 'processed' && (
              <button
                onClick={startMLProcessing}
                disabled={mlProcessing}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  mlProcessing 
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {mlProcessing ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                    Detecting Events...
                  </span>
                ) : (
                  'Detect Events with AI'
                )}
              </button>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            {video.status === 'processed' && video.metadata?.hls_manifest ? (
              <>
                <VideoPlayer 
                  ref={videoRef}
                  videoId={video.id}
                  className="w-full rounded-lg"
                  onTimeUpdate={handleTimeUpdate}
                  onError={handleVideoError}
                />
                <EventTimeline
                  events={events}
                  videoDuration={video.metadata?.duration || 0}
                  currentTime={currentTime}
                  onEventClick={jumpToEvent}
                  className="mt-4"
                />
              </>
            ) : video.status === 'processing' ? (
              <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
                <div className="text-center w-full max-w-md px-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                  <p className="text-gray-400 mb-4">Video is being processed...</p>
                  
                  {video.metadata?.processing_progress !== undefined && (
                    <>
                      <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
                        <div 
                          className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${video.metadata.processing_progress}%` }}
                        />
                      </div>
                      <p className="text-sm text-gray-500 mb-1">
                        {video.metadata.processing_stage || 'Processing...'}
                      </p>
                      <p className="text-xs text-gray-600">
                        {video.metadata.processing_quality || ''}
                      </p>
                    </>
                  )}
                  
                  <p className="text-sm text-gray-500 mt-2">This may take a few minutes</p>
                </div>
              </div>
            ) : video.status === 'failed' ? (
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
          
          <div className="lg:col-span-1 space-y-4">
            <StatsPanel events={events} />
            <EventList 
              events={events}
              onVerify={verifyEvent}
              onJump={jumpToEvent}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
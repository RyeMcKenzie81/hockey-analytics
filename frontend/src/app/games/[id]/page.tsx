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
  timestamp: number
  event_type: string
  confidence: number
  verified?: boolean
  data?: Record<string, unknown>
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
      videoRef.current.currentTime = event.timestamp
    }
  }
  
  // Memoize the time update handler to prevent re-renders
  const handleTimeUpdate = useMemo(() => {
    let lastTime = 0
    return (time: number) => {
      // Only update if time changed significantly (> 0.5 seconds)
      if (Math.abs(lastTime - time) > 0.5) {
        lastTime = time
        setCurrentTime(time)
      }
    }
  }, [])

  const verifyEvent = async (eventId: string, verified: boolean) => {
    // Update local state
    setEvents(prevEvents => 
      prevEvents.map(e => 
        e.id === eventId ? { ...e, verified } : e
      )
    )
    
    // TODO: Send verification to backend
    try {
      await axios.patch(`${API_URL}/api/events/${eventId}`, { verified })
    } catch (err) {
      console.error('Failed to verify event:', err)
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

  // Mock events for Phase 2 demo (will be replaced with real events in Phase 3)
  useEffect(() => {
    if (video?.status === 'processed' && video.metadata?.duration) {
      // Generate some sample events for demonstration
      const sampleEvents: Event[] = [
        { id: '1', timestamp: 120, event_type: 'goal', confidence: 0.95, verified: true },
        { id: '2', timestamp: 245, event_type: 'shot', confidence: 0.88 },
        { id: '3', timestamp: 380, event_type: 'penalty', confidence: 0.92 },
        { id: '4', timestamp: 520, event_type: 'save', confidence: 0.85 },
        { id: '5', timestamp: 680, event_type: 'faceoff', confidence: 0.90 },
        { id: '6', timestamp: 850, event_type: 'shot', confidence: 0.87 },
        { id: '7', timestamp: 1020, event_type: 'goal', confidence: 0.93, verified: true },
      ].filter(e => e.timestamp < (video.metadata?.duration || 0))
      
      setEvents(sampleEvents)
    }
  }, [video])
  
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
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            {video.status === 'processed' && video.metadata?.hls_manifest ? (
              <>
                <VideoPlayer 
                  key={`player-${video.id}`}  // Unique key for player instance
                  ref={videoRef}
                  videoId={video.id}
                  className="w-full rounded-lg"
                  onTimeUpdate={handleTimeUpdate}
                  onError={(error) => setError(error)}
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
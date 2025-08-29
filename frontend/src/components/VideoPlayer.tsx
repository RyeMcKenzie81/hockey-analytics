'use client'

import { useEffect, useRef, forwardRef } from 'react'
import Hls from 'hls.js'

interface VideoPlayerProps {
  videoId: string
  url?: string
  onTimeUpdate?: (time: number) => void
  onError?: (error: string) => void
  className?: string
}

export const VideoPlayer = forwardRef<HTMLVideoElement, VideoPlayerProps>(
  ({ videoId, url, onTimeUpdate, onError, className }, ref) => {
    const hlsRef = useRef<Hls | null>(null)
    const internalRef = useRef<HTMLVideoElement>(null)
    const videoRef = (ref as React.RefObject<HTMLVideoElement>) || internalRef

    useEffect(() => {
      if (!videoRef.current) return

      // Construct HLS URL if not provided
      const hlsUrl = url || `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/videos/${videoId}/hls/master.m3u8`
      
      // If HLS is already initialized with the same URL, don't reinitialize
      if (hlsRef.current && hlsRef.current.url === hlsUrl) {
        return
      }

      // Clean up previous HLS instance
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }

      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: false,
          maxBufferLength: 30,
          maxMaxBufferLength: 600,
          // Optimize for large files
          maxBufferSize: 60 * 1000 * 1000, // 60 MB
          maxBufferHole: 0.5,
          highBufferWatchdogPeriod: 2,
        })
        
        hls.loadSource(hlsUrl)
        hls.attachMedia(videoRef.current)
        
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log('HLS manifest loaded for video:', videoId)
        })
        
        hls.on(Hls.Events.ERROR, (event, data) => {
          console.error('HLS error:', data.type, data.details, data)
          
          if (data.fatal) {
            console.error('HLS fatal error:', data)
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.log('Fatal network error, attempting to recover')
                // Don't auto-recover, let user retry
                onError?.(`Network error: ${data.details}`)
                break
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.log('Fatal media error, attempting to recover')
                hls.recoverMediaError()
                break
              default:
                console.error('Fatal error, cannot recover')
                onError?.(`Playback error: ${data.details}`)
                break
            }
          } else {
            // Non-fatal errors
            console.warn('Non-fatal HLS error:', data.details)
          }
        })
        
        // Add more event listeners for debugging
        hls.on(Hls.Events.MEDIA_ATTACHED, () => {
          console.log('Media attached successfully')
        })
        
        hls.on(Hls.Events.FRAG_LOADED, (event, data) => {
          console.log('Fragment loaded:', data.frag.sn, 'duration:', data.frag.duration)
        })
        
        hlsRef.current = hls
      } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS support (Safari)
        videoRef.current.src = hlsUrl
      } else {
        onError?.('HLS is not supported in this browser')
      }

      return () => {
        if (hlsRef.current) {
          hlsRef.current.destroy()
          hlsRef.current = null
        }
      }
    }, [url, videoId, videoRef, onError])

    return (
      <video
        ref={videoRef}
        className={className || 'w-full h-auto'}
        controls
        onTimeUpdate={(e) => onTimeUpdate?.(e.currentTarget.currentTime)}
        playsInline
      />
    )
  }
)

VideoPlayer.displayName = 'VideoPlayer'
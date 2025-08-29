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

      // Clean up previous HLS instance
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }

      // Construct HLS URL if not provided
      const hlsUrl = url || `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/videos/${videoId}/hls/master.m3u8`

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
          if (data.fatal) {
            console.error('HLS fatal error:', data)
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.log('Fatal network error, attempting to recover')
                hls.startLoad()
                break
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.log('Fatal media error, attempting to recover')
                hls.recoverMediaError()
                break
              default:
                console.error('Fatal error, cannot recover')
                onError?.('Fatal playback error occurred')
                hls.destroy()
                break
            }
          }
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
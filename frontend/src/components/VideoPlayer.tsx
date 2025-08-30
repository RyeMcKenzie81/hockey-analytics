'use client'

import { useEffect, useRef, forwardRef, useCallback } from 'react'
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
    
    // Store callbacks in refs to prevent re-initialization
    const onTimeUpdateRef = useRef(onTimeUpdate)
    const onErrorRef = useRef(onError)
    
    // Update refs when props change
    useEffect(() => {
      onTimeUpdateRef.current = onTimeUpdate
    }, [onTimeUpdate])
    
    useEffect(() => {
      onErrorRef.current = onError
    }, [onError])

    // Store the URL in a ref to prevent re-initialization
    const currentUrlRef = useRef<string>('')
    const isInitializedRef = useRef<boolean>(false)
    
    useEffect(() => {
      const video = videoRef.current
      if (!video) {
        console.log('No video element ref')
        return
      }

      // Construct HLS URL if not provided
      const hlsUrl = url || `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/videos/${videoId}/hls/master.m3u8`
      
      // Prevent double initialization in React StrictMode and when URL hasn't changed
      if (isInitializedRef.current && currentUrlRef.current === hlsUrl) {
        console.log('HLS already initialized with same URL, skipping')
        return
      }
      
      console.log('Initializing VideoPlayer for video:', videoId)
      console.log('HLS URL:', hlsUrl)
      
      currentUrlRef.current = hlsUrl
      isInitializedRef.current = true

      // Clean up previous HLS instance if URL changed
      if (hlsRef.current && currentUrlRef.current !== hlsUrl) {
        console.log('URL changed, destroying previous HLS instance')
        hlsRef.current.destroy()
        hlsRef.current = null
      }

      if (Hls.isSupported() && !hlsRef.current) {
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
        hls.attachMedia(video)
        
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
                onErrorRef.current?.(`Network error: ${data.details}`)
                break
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.log('Fatal media error, attempting to recover')
                hls.recoverMediaError()
                break
              default:
                console.error('Fatal error, cannot recover')
                onErrorRef.current?.(`Playback error: ${data.details}`)
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
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS support (Safari)
        video.src = hlsUrl
      } else {
        onErrorRef.current?.('HLS is not supported in this browser')
      }

      return () => {
        if (hlsRef.current) {
          console.log('Cleanup: destroying HLS instance')
          hlsRef.current.destroy()
          hlsRef.current = null
          isInitializedRef.current = false
          currentUrlRef.current = ''
        }
      }
    }, [url, videoId]) // Removed videoRef and onError from dependencies

    // Memoized time update handler to prevent unnecessary re-renders
    const handleTimeUpdate = useCallback((e: React.SyntheticEvent<HTMLVideoElement>) => {
      onTimeUpdateRef.current?.(e.currentTarget.currentTime)
    }, [])
    
    return (
      <video
        ref={videoRef}
        className={className || 'w-full h-auto'}
        controls
        onTimeUpdate={handleTimeUpdate}
        playsInline
        preload="metadata"
      />
    )
  }
)

VideoPlayer.displayName = 'VideoPlayer'
'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

interface WebSocketMessage {
  type: string
  video_id?: string
  status?: string
  progress?: number
  error?: string
  [key: string]: unknown
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  reconnect?: boolean
  reconnectInterval?: number
}

export function useWebSocket(
  videoId: string,
  options: UseWebSocketOptions = {}
) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const reconnectAttemptsRef = useRef(0)
  const isUnmountedRef = useRef(false)
  
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnect = true,
    reconnectInterval = 3000
  } = options

  const connect = useCallback(() => {
    // Don't connect if component is unmounted or already connected
    if (isUnmountedRef.current) {
      return
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Determine WebSocket URL based on API URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const wsUrl = apiUrl.replace(/^http/, 'ws').replace(/^https/, 'wss')
    
    console.log('Connecting to WebSocket:', `${wsUrl}/api/videos/ws/${videoId}`)
    const ws = new WebSocket(`${wsUrl}/api/videos/ws/${videoId}`)
    
    ws.onopen = () => {
      console.log('WebSocket connected for video:', videoId)
      setIsConnected(true)
      reconnectAttemptsRef.current = 0 // Reset reconnect attempts on successful connection
      onOpen?.()
      
      // Clear any reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = undefined
      }
    }
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage
        console.log('WebSocket message received:', message)
        setLastMessage(message)
        onMessage?.(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
    
    ws.onerror = (error) => {
      console.warn('WebSocket error occurred')
      onError?.(error)
    }
    
    ws.onclose = (event) => {
      console.log('WebSocket disconnected, code:', event.code, 'reason:', event.reason)
      setIsConnected(false)
      wsRef.current = null
      onClose?.()
      
      // Only attempt to reconnect if enabled and component is still mounted
      if (reconnect && !isUnmountedRef.current && !event.wasClean) {
        reconnectAttemptsRef.current += 1
        
        // Use exponential backoff with max delay of 30 seconds
        const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1), 30000)
        
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`)
        
        reconnectTimeoutRef.current = setTimeout(() => {
          if (!isUnmountedRef.current) {
            connect()
          }
        }, delay)
      }
    }
    
    wsRef.current = ws
  }, [videoId, onMessage, onOpen, onClose, onError, reconnect, reconnectInterval])

  const disconnect = useCallback(() => {
    isUnmountedRef.current = true
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = undefined
    }
    
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      wsRef.current.close(1000, 'Component unmounting')
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  useEffect(() => {
    isUnmountedRef.current = false
    connect()
    
    return () => {
      disconnect()
    }
  }, [videoId, connect, disconnect])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    reconnect: connect,
    disconnect
  }
}
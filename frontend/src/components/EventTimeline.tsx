'use client'

import { useState, useRef } from 'react'

interface Event {
  id: string
  timestamp: number
  event_type: string
  confidence: number
  verified?: boolean
  data?: Record<string, unknown>
}

interface EventTimelineProps {
  events: Event[]
  videoDuration: number
  currentTime: number
  onEventClick: (event: Event) => void
  className?: string
}

export function EventTimeline({ 
  events, 
  videoDuration, 
  currentTime, 
  onEventClick,
  className = ''
}: EventTimelineProps) {
  const timelineRef = useRef<HTMLDivElement>(null)
  const [hoveredEvent, setHoveredEvent] = useState<Event | null>(null)

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'goal':
        return 'bg-green-500'
      case 'shot':
        return 'bg-blue-500'
      case 'penalty':
        return 'bg-red-500'
      case 'save':
        return 'bg-yellow-500'
      case 'faceoff':
        return 'bg-purple-500'
      default:
        return 'bg-gray-500'
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getEventPosition = (timestamp: number) => {
    if (!videoDuration) return 0
    return (timestamp / videoDuration) * 100
  }

  const getCurrentTimePosition = () => {
    if (!videoDuration) return 0
    return (currentTime / videoDuration) * 100
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-300">Event Timeline</h3>
        <span className="text-xs text-gray-400">
          {formatTime(currentTime)} / {formatTime(videoDuration)}
        </span>
      </div>
      
      <div className="relative" ref={timelineRef}>
        {/* Timeline track */}
        <div className="h-2 bg-gray-700 rounded-full relative">
          {/* Progress bar */}
          <div 
            className="absolute top-0 left-0 h-full bg-gray-500 rounded-full transition-all duration-100"
            style={{ width: `${getCurrentTimePosition()}%` }}
          />
          
          {/* Current time indicator */}
          <div 
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg z-20"
            style={{ left: `${getCurrentTimePosition()}%`, transform: 'translate(-50%, -50%)' }}
          />
        </div>
        
        {/* Event markers */}
        <div className="relative h-8 mt-2">
          {events.map((event) => (
            <div
              key={event.id}
              className="absolute -translate-x-1/2 cursor-pointer group"
              style={{ left: `${getEventPosition(event.timestamp)}%` }}
              onClick={() => onEventClick(event)}
              onMouseEnter={() => setHoveredEvent(event)}
              onMouseLeave={() => setHoveredEvent(null)}
            >
              {/* Event marker */}
              <div 
                className={`w-2 h-6 rounded-sm ${getEventColor(event.event_type)} 
                  ${event.verified ? 'opacity-100' : 'opacity-60'}
                  hover:scale-110 transition-transform`}
              />
              
              {/* Tooltip */}
              {hoveredEvent?.id === event.id && (
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-30 whitespace-nowrap">
                  <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 shadow-lg">
                    <div className="font-semibold capitalize">{event.event_type.replace('_', ' ')}</div>
                    <div className="text-gray-400">{formatTime(event.timestamp)}</div>
                    {event.confidence && (
                      <div className="text-gray-400">
                        Confidence: {Math.round(event.confidence * 100)}%
                      </div>
                    )}
                  </div>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1">
                    <div className="border-4 border-transparent border-t-gray-900" />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Time markers */}
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>0:00</span>
          <span>{formatTime(videoDuration / 4)}</span>
          <span>{formatTime(videoDuration / 2)}</span>
          <span>{formatTime((videoDuration * 3) / 4)}</span>
          <span>{formatTime(videoDuration)}</span>
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-500 rounded-sm" />
          <span className="text-gray-400">Goal</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-blue-500 rounded-sm" />
          <span className="text-gray-400">Shot</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-500 rounded-sm" />
          <span className="text-gray-400">Penalty</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-yellow-500 rounded-sm" />
          <span className="text-gray-400">Save</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-purple-500 rounded-sm" />
          <span className="text-gray-400">Faceoff</span>
        </div>
      </div>
    </div>
  )
}
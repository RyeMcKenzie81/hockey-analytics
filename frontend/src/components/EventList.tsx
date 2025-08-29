'use client'

import { useState } from 'react'

interface Event {
  id: string
  timestamp: number
  event_type: string
  confidence: number
  verified?: boolean
  data?: Record<string, unknown>
}

interface EventListProps {
  events: Event[]
  onVerify: (eventId: string, verified: boolean) => void
  onJump: (event: Event) => void
  className?: string
}

export function EventList({ 
  events, 
  onVerify, 
  onJump,
  className = ''
}: EventListProps) {
  const [filter, setFilter] = useState<string>('all')
  const [showUnverified, setShowUnverified] = useState(true)

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'goal':
        return '🥅'
      case 'shot':
        return '🏒'
      case 'penalty':
        return '⚠️'
      case 'save':
        return '🧤'
      case 'faceoff':
        return '⭕'
      default:
        return '📍'
    }
  }

  const filteredEvents = events.filter(event => {
    if (filter !== 'all' && event.event_type !== filter) return false
    if (!showUnverified && !event.verified) return false
    return true
  })

  const eventTypes = ['all', ...Array.from(new Set(events.map(e => e.event_type)))]

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Events</h2>
        <span className="text-sm text-gray-400">{filteredEvents.length} events</span>
      </div>

      {/* Filters */}
      <div className="mb-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          {eventTypes.map(type => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                filter === type
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {type === 'all' ? 'All' : type.replace('_', ' ')}
            </button>
          ))}
        </div>
        
        <label className="flex items-center gap-2 text-sm text-gray-400">
          <input
            type="checkbox"
            checked={showUnverified}
            onChange={(e) => setShowUnverified(e.target.checked)}
            className="rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-blue-500"
          />
          Show unverified events
        </label>
      </div>

      {/* Event list */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredEvents.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-4">
            No events found
          </p>
        ) : (
          filteredEvents.map((event) => (
            <div
              key={event.id}
              className="bg-gray-700 rounded-lg p-3 hover:bg-gray-650 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{getEventIcon(event.event_type)}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium capitalize">
                          {event.event_type.replace('_', ' ')}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatTime(event.timestamp)}
                        </span>
                      </div>
                      {event.confidence && (
                        <div className="text-xs text-gray-500">
                          Confidence: {Math.round(event.confidence * 100)}%
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Verification buttons */}
                  <div className="flex gap-1">
                    <button
                      onClick={() => onVerify(event.id, true)}
                      className={`p-1 rounded transition-colors ${
                        event.verified === true
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-600 text-gray-400 hover:bg-green-600 hover:text-white'
                      }`}
                      title="Verify event"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </button>
                    <button
                      onClick={() => onVerify(event.id, false)}
                      className={`p-1 rounded transition-colors ${
                        event.verified === false
                          ? 'bg-red-600 text-white'
                          : 'bg-gray-600 text-gray-400 hover:bg-red-600 hover:text-white'
                      }`}
                      title="Mark as incorrect"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  {/* Jump to event button */}
                  <button
                    onClick={() => onJump(event)}
                    className="p-1 bg-gray-600 text-gray-300 rounded hover:bg-blue-600 hover:text-white transition-colors"
                    title="Jump to event"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
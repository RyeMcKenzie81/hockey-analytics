'use client'

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

interface StatsPanelProps {
  events: Event[]
  className?: string
}

export function StatsPanel({ events, className = '' }: StatsPanelProps) {
  // Calculate statistics
  const stats = events.reduce((acc, event) => {
    const type = event.event_type
    if (!acc[type]) {
      acc[type] = { total: 0, verified: 0 }
    }
    acc[type].total++
    if (event.verified) {
      acc[type].verified++
    }
    return acc
  }, {} as Record<string, { total: number; verified: number }>)

  const totalEvents = events.length
  const verifiedEvents = events.filter(e => e.verified).length
  const verificationRate = totalEvents > 0 ? (verifiedEvents / totalEvents) * 100 : 0

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'goal':
        return 'text-green-400'
      case 'shot':
        return 'text-blue-400'
      case 'penalty':
        return 'text-red-400'
      case 'save':
        return 'text-yellow-400'
      case 'faceoff':
        return 'text-purple-400'
      default:
        return 'text-gray-400'
    }
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      <h2 className="text-lg font-semibold text-white mb-4">Game Statistics</h2>
      
      {/* Overall stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-700 rounded p-3">
          <div className="text-2xl font-bold text-white">{totalEvents}</div>
          <div className="text-xs text-gray-400">Total Events</div>
        </div>
        <div className="bg-gray-700 rounded p-3">
          <div className="text-2xl font-bold text-green-400">
            {verificationRate.toFixed(0)}%
          </div>
          <div className="text-xs text-gray-400">Verified</div>
        </div>
      </div>
      
      {/* Event breakdown */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-300">Event Breakdown</h3>
        
        {Object.entries(stats)
          .sort((a, b) => b[1].total - a[1].total)
          .map(([eventType, data]) => (
            <div key={eventType} className="flex items-center justify-between">
              <div className="flex items-center gap-2 flex-1">
                <span className={`capitalize font-medium ${getEventColor(eventType)}`}>
                  {eventType.replace('_', ' ')}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-white font-semibold">{data.total}</span>
                {data.verified > 0 && (
                  <span className="text-xs text-green-400">
                    ({data.verified} ✓)
                  </span>
                )}
              </div>
            </div>
          ))}
        
        {Object.keys(stats).length === 0 && (
          <p className="text-gray-400 text-sm text-center py-4">
            No events detected yet
          </p>
        )}
      </div>
      
      {/* Period breakdown (placeholder for now) */}
      <div className="mt-6 pt-4 border-t border-gray-700">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Period Breakdown</h3>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-gray-700 rounded p-2">
            <div className="text-xs text-gray-400">1st</div>
            <div className="text-sm font-semibold text-white">-</div>
          </div>
          <div className="bg-gray-700 rounded p-2">
            <div className="text-xs text-gray-400">2nd</div>
            <div className="text-sm font-semibold text-white">-</div>
          </div>
          <div className="bg-gray-700 rounded p-2">
            <div className="text-xs text-gray-400">3rd</div>
            <div className="text-sm font-semibold text-white">-</div>
          </div>
        </div>
      </div>
      
      {/* Export button (placeholder) */}
      <button className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
        Export Statistics
      </button>
    </div>
  )
}
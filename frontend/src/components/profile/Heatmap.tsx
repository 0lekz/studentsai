/**
 * Heatmap: GitHub-like activity heatmap that fills the full canvas space.
 * Expects UTC date strings (YYYY-MM-DD). Buckets: 0, 1–2, 3–5, 6–9, 10+.
 */
'use client'

import { useMemo, useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import type { ActivityDayCount } from '@/lib/api'

interface HeatmapProps {
  title?: string
  days: ActivityDayCount[]
}

export function Heatmap({ title = 'Activity', days }: HeatmapProps) {
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [tooltip, setTooltip] = useState<{ content: string; x: number; y: number } | null>(null)

  // Theme-aware color function
  const getColorClass = (bucket: number, isDark: boolean) => {
    if (isDark) {
      const darkPalette = ['#0b0f14', '#19212b', '#2a3442', '#f97316', '#ea580c']
      return darkPalette[bucket]
    } else {
      const lightPalette = ['#f3f4f6', '#e5e7eb', '#d1d5db', '#fb923c', '#ea580c']
      return lightPalette[bucket]
    }
  }

  // Format date for tooltip display
  const formatDate = (dateStr: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr + 'T00:00:00Z')
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })
  }

  // Detect theme after component mounts
  useEffect(() => {
    const checkTheme = () => {
      const isDark = document.documentElement.classList.contains('dark')
      setIsDarkMode(isDark)
    }
    
    checkTheme()
    
    // Listen for theme changes
    const observer = new MutationObserver(checkTheme)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    
    return () => observer.disconnect()
  }, [])
  
  const grid = useMemo(() => {
    // Arrange as columns by week: each column has 7 entries (Sun..Sat)
    // days is expected continuous oldest->newest; ensure we start on Sunday column boundary
    if (!days || days.length === 0) return [] as ActivityDayCount[][]
    
    // Build Date objects
    const parsed = days.map(d => ({ ...d, _date: new Date(d.date + 'T00:00:00Z') }))
    
    // Find the weekday (0..6) of first day (UTC) and pre-pad if needed
    const firstW = parsed[0]._date.getUTCDay()
    const padded: ActivityDayCount[] = []
    for (let i = 0; i < firstW; i++) padded.push({ date: '', count: 0 })
    for (const d of parsed) padded.push({ date: d.date, count: d.count, top_type: d.top_type })
    
    // Chunk into columns of 7
    const cols: ActivityDayCount[][] = []
    for (let i = 0; i < padded.length; i += 7) {
      cols.push(padded.slice(i, i + 7))
    }
    return cols
  }, [days])

  const bucket = (c: number) => {
    if (c <= 0) return 0
    if (c <= 2) return 1
    if (c <= 5) return 2
    if (c <= 9) return 3
    return 4
  }

  // If no days, show empty state
  if (!days || days.length === 0) {
    return (
      <Card className="border border-gray-200 dark:border-[#232a36] bg-white dark:bg-[#141820]">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-900 dark:text-gray-200">{title}</h2>
            <div className="text-xs text-gray-600 dark:text-gray-400">No activity data</div>
          </div>
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <p>No activity recorded yet.</p>
            <p className="text-xs mt-2">Create notes or review flashcards to see your activity here.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border border-gray-200 dark:border-[#232a36] bg-white dark:bg-[#141820]">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-gray-900 dark:text-gray-200">{title}</h2>
          <div className="text-xs text-gray-600 dark:text-gray-400">UTC last {days.length} days</div>
        </div>
        
        {/* Heatmap container that fills available space */}
        <div className="w-full relative">
          <div 
            className="flex gap-1 w-full" 
            role="grid" 
            aria-label="Activity heatmap"
            style={{ 
              minHeight: '120px',
              justifyContent: 'space-between'
            }}
          >
            {grid.map((col, ci) => (
              <div 
                key={ci} 
                className="flex flex-col gap-1 flex-1"
                style={{ 
                  minHeight: '120px',
                  justifyContent: 'space-between'
                }}
              >
                {col.map((d, ri) => (
                  <div
                    key={`${ci}-${ri}-${d.date}`}
                    role="gridcell"
                    aria-label={d.date ? `${d.date} ${d.count} activities` : ''}
                    className="flex-1 min-h-[12px] rounded-sm ring-1 ring-gray-200 dark:ring-white/10 transition-all duration-200 hover:ring-2 hover:ring-orange-500/50 hover:scale-110 cursor-pointer"
                    style={{ 
                      backgroundColor: getColorClass(bucket(d.count || 0), isDarkMode),
                      minHeight: '12px',
                      maxHeight: '16px'
                    }}
                    onMouseEnter={(e) => {
                      if (d.date) {
                        const rect = e.currentTarget.getBoundingClientRect()
                        const content = `${formatDate(d.date)}\n${d.count} activities${d.top_type ? `\nMost common: ${d.top_type}` : ''}`
                        setTooltip({
                          content,
                          x: rect.left + rect.width / 2,
                          y: rect.top - 10
                        })
                      }
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                ))}
              </div>
            ))}
          </div>

          {/* GitHub-style tooltip */}
          {tooltip && (
            <div
              className="fixed z-50 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg pointer-events-none whitespace-pre-line text-center"
              style={{
                left: tooltip.x,
                top: tooltip.y,
                transform: 'translateX(-50%) translateY(-100%)'
              }}
            >
              {tooltip.content}
              <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
            </div>
          )}
        </div>
        
        {/* Legend */}
        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
            <span>Less</span>
            <div className="flex gap-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: getColorClass(i, isDarkMode) }}
                />
              ))}
            </div>
            <span>More</span>
          </div>
          <div className="text-[11px] text-gray-500 dark:text-gray-500">Note: All activity uses UTC.</div>
        </div>
      </CardContent>
    </Card>
  )
}



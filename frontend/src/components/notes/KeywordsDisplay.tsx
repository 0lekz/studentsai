'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Hash, RefreshCw, X } from 'lucide-react'
import { type Note } from '@/lib/api'

interface KeywordsDisplayProps {
  note: Note
  onRefreshKeywords?: (noteId: string) => Promise<void>
  onRemoveKeyword?: (keyword: string) => void
  className?: string
}

export function KeywordsDisplay({ 
  note, 
  onRefreshKeywords, 
  onRemoveKeyword,
  className = '' 
}: KeywordsDisplayProps) {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isRemoving, setIsRemoving] = useState<string | null>(null)

  const keywords = note.tags || []

  const handleRefreshKeywords = async () => {
    if (!onRefreshKeywords) return
    
    setIsRefreshing(true)
    try {
      await onRefreshKeywords(note.id)
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleRemoveKeyword = async (keyword: string) => {
    if (!onRemoveKeyword) return
    
    setIsRemoving(keyword)
    try {
      await onRemoveKeyword(keyword)
    } finally {
      setIsRemoving(null)
    }
  }

  if (keywords.length === 0) {
    return (
      <div className={`flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400 ${className}`}>
        <Hash className="h-4 w-4" />
        <span>No keywords extracted</span>
        {onRefreshKeywords && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefreshKeywords}
            disabled={isRefreshing}
            className="h-6 px-2 text-xs"
          >
            {isRefreshing ? (
              <>
                <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                Extracting...
              </>
            ) : (
              <>
                <RefreshCw className="h-3 w-3 mr-1" />
                Extract Keywords
              </>
            )}
          </Button>
        )}
      </div>
    )
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Hash className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Keywords ({keywords.length})
          </span>
        </div>
        {onRefreshKeywords && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefreshKeywords}
            disabled={isRefreshing}
            className="h-6 px-2 text-xs"
          >
            {isRefreshing ? (
              <>
                <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                Refreshing...
              </>
            ) : (
              <>
                <RefreshCw className="h-3 w-3 mr-1" />
                Refresh
              </>
            )}
          </Button>
        )}
      </div>
      
      <div className="flex flex-wrap gap-2">
        {keywords.map((keyword) => (
          <Badge
            key={keyword}
            variant="secondary"
            className="group relative px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 border border-orange-200 dark:border-orange-800"
          >
            {keyword}
            {onRemoveKeyword && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleRemoveKeyword(keyword)}
                disabled={isRemoving === keyword}
                className="h-4 w-4 p-0 ml-1 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-orange-200 dark:hover:bg-orange-800"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </Badge>
        ))}
      </div>
    </div>
  )
}

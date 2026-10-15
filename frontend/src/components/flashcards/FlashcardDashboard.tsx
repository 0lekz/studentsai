'use client'

import { useState } from 'react'
import { Play, RefreshCw } from 'lucide-react'
import { api, type Flashcard } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { SectionToolbar } from '@/components/course/SectionToolbar'
import { FlashcardFilters } from './FlashcardFilters'
import { FlashcardGrid } from './FlashcardGrid'
import { StudySession } from './StudySession'
import { useFlashcardCollection } from './useFlashcardCollection'

const rateFlashcard = (card: Flashcard, quality: number) => api.reviewFlashcard(card.id, quality)

interface FlashcardDashboardProps {
  courseId?: string
  emptyState: React.ReactNode
}

export function FlashcardDashboard({ courseId, emptyState }: FlashcardDashboardProps) {
  const collection = useFlashcardCollection(courseId)
  const [session, setSession] = useState<{ key: number; startIndex: number } | null>(null)
  const { flashcards, filteredFlashcards, loading, searchQuery, selectedTags } = collection
  const filtersActive = searchQuery.trim() !== '' || selectedTags.length > 0

  const startSession = (startIndex: number = 0) => {
    if (filteredFlashcards.length === 0) return
    setSession((current) => ({ key: (current?.key ?? 0) + 1, startIndex }))
  }

  if (loading && flashcards.length === 0 && !filtersActive) {
    return <Spinner label="Loading flashcards" />
  }

  if (flashcards.length === 0 && !filtersActive) {
    return <>{emptyState}</>
  }

  if (session && filteredFlashcards.length > 0) {
    return (
      <StudySession
        key={session.key}
        cards={filteredFlashcards}
        initialIndex={session.startIndex}
        onRate={rateFlashcard}
        onExit={() => {
          setSession(null)
          collection.refresh()
        }}
      />
    )
  }

  return (
    <div>
      <SectionToolbar
        title="Practice"
        description={pluralize(flashcards.length, 'flashcard')}
        action={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" aria-label="Refresh flashcards" onClick={collection.refresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button onClick={() => startSession()} disabled={filteredFlashcards.length === 0}>
              <Play className="h-4 w-4" />
              Start session
            </Button>
          </div>
        }
      />
      <FlashcardFilters
        searchQuery={collection.searchQuery}
        onSearchQueryChange={collection.setSearchQuery}
        onSearch={collection.search}
        onClear={collection.clearFilters}
        searching={collection.loading}
        availableTags={collection.availableTags}
        selectedTags={collection.selectedTags}
        onToggleTag={collection.toggleTag}
        shownCount={filteredFlashcards.length}
        totalCount={flashcards.length}
      />
      <div className="mt-6">
        <FlashcardGrid flashcards={filteredFlashcards} onStudy={startSession} />
      </div>
    </div>
  )
}

import { Clock, Play } from 'lucide-react'
import type { Flashcard } from '@/lib/api'
import { formatShortDate, pluralize } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface FlashcardGridProps {
  flashcards: Flashcard[]
  onStudy: (index: number) => void
}

export function FlashcardGrid({ flashcards, onStudy }: FlashcardGridProps) {
  return (
    <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {flashcards.map((flashcard, index) => (
        <li key={flashcard.id} className="flex flex-col rounded-card border border-border bg-surface p-4 shadow-sm">
          <h3 className="line-clamp-2 text-body font-medium text-foreground">{flashcard.question}</h3>
          <p className="mt-2 flex items-center gap-1.5 text-caption text-muted-foreground">
            <Clock className="h-3.5 w-3.5" aria-hidden />
            {flashcard.review_count > 0
              ? `${pluralize(flashcard.review_count, 'review')}${flashcard.last_reviewed ? ` · last ${formatShortDate(flashcard.last_reviewed)}` : ''}`
              : 'Not reviewed yet'}
          </p>
          {flashcard.tags && flashcard.tags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {flashcard.tags.map((tag) => (
                <Badge key={tag} variant="secondary">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
          <Button variant="outline" size="sm" onClick={() => onStudy(index)} className="mt-4 w-full">
            <Play className="h-4 w-4" />
            Study
          </Button>
        </li>
      ))}
    </ul>
  )
}

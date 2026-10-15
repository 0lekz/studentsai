import { Search, Tag } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface FlashcardFiltersProps {
  searchQuery: string
  onSearchQueryChange: (query: string) => void
  onSearch: () => void
  onClear: () => void
  searching: boolean
  availableTags: string[]
  selectedTags: string[]
  onToggleTag: (tag: string) => void
  shownCount: number
  totalCount: number
}

export function FlashcardFilters({
  searchQuery,
  onSearchQueryChange,
  onSearch,
  onClear,
  searching,
  availableTags,
  selectedTags,
  onToggleTag,
  shownCount,
  totalCount,
}: FlashcardFiltersProps) {
  return (
    <div className="space-y-4">
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault()
          onSearch()
        }}
      >
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
            placeholder="Search by question or answer"
            aria-label="Search flashcards"
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <Button type="submit" variant="outline" disabled={searching} className="flex-1 sm:flex-none">
            {searching ? 'Searching...' : 'Search'}
          </Button>
          <Button type="button" variant="ghost" onClick={onClear} className="flex-1 sm:flex-none">
            Clear
          </Button>
        </div>
      </form>

      {availableTags.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <Tag className="h-4 w-4 text-muted-foreground" aria-label="Filter by tags" />
          {availableTags.map((tag) => {
            const selected = selectedTags.includes(tag)
            return (
              <button
                key={tag}
                type="button"
                aria-pressed={selected}
                onClick={() => onToggleTag(tag)}
                className={cn(
                  'rounded-full border px-3 py-1 text-caption font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  selected ? 'border-transparent bg-primary text-primary-foreground' : 'border-border bg-surface text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                {tag}
              </button>
            )
          })}
        </div>
      )}

      <p className="text-caption text-muted-foreground">
        Showing {shownCount} of {totalCount} flashcards
        {selectedTags.length > 0 && ` · Filtered by ${selectedTags.join(', ')}`}
      </p>
    </div>
  )
}

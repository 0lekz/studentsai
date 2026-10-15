'use client'

import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { type Note } from '@/lib/api'
import { cn, formatDate, getWordCount } from '@/lib/utils'
import {
  Calendar,
  Clock,
  Edit,
  FileText,
  Filter,
  Hash,
  MoreHorizontal,
  Search,
  SortAsc,
  SortDesc,
  Tag,
  Trash2,
  X,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'

interface NotesListProps {
  notes: Note[]
  onEdit: (note: Note) => void
  onDelete: (noteId: string) => Promise<void> | void
  onSelect: (note: Note) => void
  selectedNoteId?: string
}

type SortOption = 'updated' | 'created' | 'title' | 'wordCount'
type SortDirection = 'asc' | 'desc'

const SORT_LABELS: Record<SortOption, string> = {
  updated: 'Updated',
  created: 'Created',
  title: 'Title',
  wordCount: 'Length',
}

const SORT_ICONS: Record<SortOption, typeof Clock> = {
  updated: Clock,
  created: Calendar,
  title: FileText,
  wordCount: Hash,
}

export function NotesList({ notes, onEdit, onDelete, onSelect, selectedNoteId }: NotesListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteDialog, setDeleteDialog] = useState<{ isOpen: boolean; noteId: string | null }>({
    isOpen: false,
    noteId: null,
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<SortOption>('updated')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [showFilters, setShowFilters] = useState(false)

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.noteId) return
    setDeletingId(deleteDialog.noteId)
    try {
      await onDelete(deleteDialog.noteId)
    } finally {
      setDeletingId(null)
    }
  }

  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    for (const note of notes) {
      for (const tag of note.tags ?? []) tagSet.add(tag)
    }
    return Array.from(tagSet).sort()
  }, [notes])

  const filteredAndSortedNotes = useMemo(() => {
    const query = searchQuery.toLowerCase()
    const filtered = notes.filter((note) => {
      if (query) {
        const matchesTitle = note.title.toLowerCase().includes(query)
        const matchesContent = note.content.toLowerCase().includes(query)
        const matchesTags = note.tags?.some((tag) => tag.toLowerCase().includes(query))
        if (!matchesTitle && !matchesContent && !matchesTags) return false
      }
      if (selectedTag) {
        return note.tags?.includes(selectedTag) || false
      }
      return true
    })

    filtered.sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'title':
          comparison = a.title.localeCompare(b.title)
          break
        case 'created':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          break
        case 'updated':
          comparison = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
          break
        case 'wordCount':
          comparison = getWordCount(a.content) - getWordCount(b.content)
          break
      }
      return sortDirection === 'asc' ? comparison : -comparison
    })

    return filtered
  }, [notes, searchQuery, selectedTag, sortBy, sortDirection])

  const handleSort = (option: SortOption) => {
    if (sortBy === option) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(option)
      setSortDirection('desc')
    }
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedTag(null)
    setSortBy('updated')
    setSortDirection('desc')
  }

  if (notes.length === 0) {
    return (
      <div className="p-6 text-center">
        <FileText className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
        <p className="text-body text-foreground">No notes yet</p>
        <p className="mt-1 text-caption text-muted-foreground">Write your first note for this course.</p>
      </div>
    )
  }

  const SortIcon = SORT_ICONS[sortBy]

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="space-y-3 border-b border-border p-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search notes..."
            aria-label="Search notes"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 bg-background pl-9"
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            {allTags.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                aria-pressed={showFilters}
                onClick={() => setShowFilters(!showFilters)}
                className={cn('h-8 px-2 text-muted-foreground', showFilters && 'bg-brand-soft text-brand-soft-foreground')}
              >
                <Filter className="h-4 w-4" />
                Tags
              </Button>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground">
                  <SortIcon className="h-4 w-4" />
                  {SORT_LABELS[sortBy]}
                  {sortDirection === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onClick={() => handleSort('updated')}>
                  <Clock className="h-4 w-4" />
                  Last updated
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSort('created')}>
                  <Calendar className="h-4 w-4" />
                  Date created
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSort('title')}>
                  <FileText className="h-4 w-4" />
                  Title
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSort('wordCount')}>
                  <Hash className="h-4 w-4" />
                  Word count
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {(searchQuery || selectedTag) && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="h-8 px-2 text-muted-foreground">
                <X className="h-4 w-4" />
                Clear
              </Button>
            )}
          </div>

          <span className="text-caption text-muted-foreground">
            {filteredAndSortedNotes.length} of {notes.length}
          </span>
        </div>

        {showFilters && allTags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {allTags.map((tag) => (
              <button
                key={tag}
                type="button"
                aria-pressed={selectedTag === tag}
                onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                className={cn(
                  'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-caption transition-colors',
                  selectedTag === tag ? 'border-transparent bg-primary text-primary-foreground' : 'border-border text-muted-foreground hover:bg-accent'
                )}
              >
                <Tag className="h-3 w-3" />
                {tag}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <ul className="space-y-0.5 p-2">
          {filteredAndSortedNotes.map((note) => (
            <li
              key={note.id}
              className={cn(
                'group relative flex cursor-pointer items-center gap-3 rounded-control border-l-2 px-3 py-2 transition-colors',
                selectedNoteId === note.id ? 'border-brand bg-brand-soft' : 'border-transparent hover:bg-accent'
              )}
              onClick={() => onSelect(note)}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-body font-medium text-foreground">{note.title}</p>
                <p className="truncate text-caption text-muted-foreground">
                  {formatDate(note.updated_at)} · {getWordCount(note.content)} words
                </p>
                {note.tags && note.tags.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {note.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className="inline-flex items-center gap-1 rounded-full bg-muted px-1.5 py-0.5 text-caption text-muted-foreground">
                        <Tag className="h-2.5 w-2.5" />
                        {tag}
                      </span>
                    ))}
                    {note.tags.length > 3 && (
                      <span className="rounded-full bg-muted px-1.5 py-0.5 text-caption text-muted-foreground">+{note.tags.length - 3}</span>
                    )}
                  </div>
                )}
              </div>

              <div className="shrink-0 transition-opacity focus-within:opacity-100 md:opacity-0 md:group-hover:opacity-100">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Options for ${note.title}`}
                      className="text-muted-foreground"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation()
                        onEdit(note)
                      }}
                    >
                      <Edit className="h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation()
                        setDeleteDialog({ isOpen: true, noteId: note.id })
                      }}
                      disabled={deletingId === note.id}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                      {deletingId === note.id ? 'Deleting...' : 'Delete'}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <ConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={() => setDeleteDialog({ isOpen: false, noteId: null })}
        onConfirm={handleDeleteConfirm}
        title="Delete note"
        description="Delete this note? This cannot be undone and also removes its flashcards."
        confirmText="Delete note"
        cancelText="Cancel"
        variant="destructive"
      />
    </div>
  )
}

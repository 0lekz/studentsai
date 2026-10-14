'use client'

import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { type Note } from '@/lib/api'
import { formatDate, getWordCount } from '@/lib/utils'
import { 
  Edit, 
  Trash2, 
  FileText, 
  Calendar, 
  Hash, 
  MoreHorizontal, 
  Search, 
  Filter, 
  SortAsc, 
  SortDesc,
  Tag,
  Clock,
  X
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { Badge } from '@/components/ui/badge'

interface NotesListProps {
  notes: Note[]
  onEdit: (note: Note) => void
  onDelete: (noteId: string) => void
  onSelect: (note: Note) => void
  onRefreshKeywords?: (noteId: string) => Promise<void>
  selectedNoteId?: string
}

type SortOption = 'updated' | 'created' | 'title' | 'wordCount'
type SortDirection = 'asc' | 'desc'

export function NotesList({ notes, onEdit, onDelete, onSelect, selectedNoteId }: NotesListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteDialog, setDeleteDialog] = useState<{ isOpen: boolean; noteId: string | null }>({
    isOpen: false,
    noteId: null
  })
  
  // Filter and sort state
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<SortOption>('updated')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [showFilters, setShowFilters] = useState(false)

  const handleDeleteClick = (noteId: string) => {
    setDeleteDialog({ isOpen: true, noteId })
  }

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.noteId) return
    
    setDeletingId(deleteDialog.noteId)
    try {
      await onDelete(deleteDialog.noteId)
    } finally {
      setDeletingId(null)
    }
  }

  const closeDeleteDialog = () => {
    setDeleteDialog({ isOpen: false, noteId: null })
  }

  // Get all unique tags from notes
  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    notes.forEach(note => {
      if (note.tags) {
        note.tags.forEach(tag => tagSet.add(tag))
      }
    })
    return Array.from(tagSet).sort()
  }, [notes])

  // Filter and sort notes
  const filteredAndSortedNotes = useMemo(() => {
    const filtered = notes.filter(note => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesTitle = note.title.toLowerCase().includes(query)
        const matchesContent = note.content.toLowerCase().includes(query)
        const matchesTags = note.tags?.some(tag => tag.toLowerCase().includes(query))
        if (!matchesTitle && !matchesContent && !matchesTags) return false
      }
      
      // Tag filter
      if (selectedTag) {
        return note.tags?.includes(selectedTag) || false
      }
      
      return true
    })

    // Sort notes
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
      <div className="p-4 text-center">
        <FileText className="h-8 w-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No notes yet</p>
        <p className="text-xs text-gray-400 mt-1 dark:text-gray-500">Create your first note to get started</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search and Filter Bar */}
      <div className="p-3 border-b border-gray-200 dark:border-[#232a36] space-y-3">
        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-gray-50 dark:bg-[#0f1115] border-gray-200 dark:border-[#232a36] text-gray-900 dark:text-gray-100"
          />
        </div>

        {/* Filter Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className={`h-8 px-2 ${showFilters ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            >
              <Filter className="h-4 w-4 mr-1" />
              Filters
            </Button>
            
            {/* Sort Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 px-2">
                  {sortBy === 'updated' && <Clock className="h-4 w-4 mr-1" />}
                  {sortBy === 'created' && <Calendar className="h-4 w-4 mr-1" />}
                  {sortBy === 'title' && <FileText className="h-4 w-4 mr-1" />}
                  {sortBy === 'wordCount' && <Hash className="h-4 w-4 mr-1" />}
                  {sortBy === 'updated' ? 'Updated' : sortBy === 'created' ? 'Created' : sortBy === 'title' ? 'Title' : 'Length'}
                  {sortDirection === 'asc' ? <SortAsc className="h-4 w-4 ml-1" /> : <SortDesc className="h-4 w-4 ml-1" />}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onClick={() => handleSort('updated')}>
                  <Clock className="h-4 w-4 mr-2" />
                  Last Updated
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSort('created')}>
                  <Calendar className="h-4 w-4 mr-2" />
                  Date Created
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSort('title')}>
                  <FileText className="h-4 w-4 mr-2" />
                  Title
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleSort('wordCount')}>
                  <Hash className="h-4 w-4 mr-2" />
                  Word Count
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Clear Filters */}
            {(searchQuery || selectedTag) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="h-8 px-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <X className="h-4 w-4 mr-1" />
                Clear
              </Button>
            )}
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400">
            {filteredAndSortedNotes.length} of {notes.length}
          </div>
        </div>

        {/* Tag Filters */}
        {showFilters && allTags.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-gray-700 dark:text-gray-300">Filter by tags:</div>
            <div className="flex flex-wrap gap-1">
              {allTags.map(tag => (
                <Badge
                  key={tag}
                  variant={selectedTag === tag ? "default" : "outline"}
                  className={`cursor-pointer text-xs ${
                    selectedTag === tag 
                      ? 'bg-orange-500 text-white hover:bg-orange-600' 
                      : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                >
                  <Tag className="h-3 w-3 mr-1" />
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Notes List */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-1 p-2">
          {filteredAndSortedNotes.map((note) => (
            <div
              key={note.id}
              className={`group relative flex items-center space-x-3 rounded-lg px-3 py-2 cursor-pointer transition-colors border-l-2 ${
                selectedNoteId === note.id
                  ? 'bg-orange-50 border-orange-500 dark:bg-orange-950/20 dark:border-orange-400'
                  : 'hover:bg-gray-100 border-transparent dark:hover:bg-[#0f1115]'
              }`}
              onClick={() => onSelect(note)}
            >
          {/* Note Icon */}
          <div className="flex-shrink-0">
            <FileText className="h-4 w-4 text-gray-500" />
          </div>

          {/* Note Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate dark:text-gray-100">
              {note.title}
            </p>
            <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
              <span>{formatDate(note.updated_at)}</span>
              <span>•</span>
              <span>{getWordCount(note.content)} words</span>
            </div>
            
            {/* Tags */}
            {note.tags && note.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {note.tags.slice(0, 3).map(tag => (
                  <Badge
                    key={tag}
                    variant="outline"
                    className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600"
                  >
                    <Tag className="h-2.5 w-2.5 mr-1" />
                    {tag}
                  </Badge>
                ))}
                {note.tags.length > 3 && (
                  <Badge
                    variant="outline"
                    className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600"
                  >
                    +{note.tags.length - 3}
                  </Badge>
                )}
              </div>
            )}

          </div>

          {/* Actions */}
          <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 dark:text-gray-300 dark:hover:bg-[#0f1115]"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={(e: React.MouseEvent) => {
                  e.stopPropagation()
                  onEdit(note)
                }}>
                  <Edit className="h-3 w-3 mr-2" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem 
                  onClick={(e: React.MouseEvent) => {
                    e.stopPropagation()
                    handleDeleteClick(note.id)
                  }}
                  disabled={deletingId === note.id}
                  className="text-red-600 dark:text-red-400"
                >
                  <Trash2 className="h-3 w-3 mr-2" />
                  {deletingId === note.id ? 'Deleting...' : 'Delete'}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          </div>
          ))}
        </div>
      </div>
      
      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={closeDeleteDialog}
        onConfirm={handleDeleteConfirm}
        title="Delete Note"
        description="Are you sure you want to delete this note? This action cannot be undone and will also remove any associated flashcards."
        confirmText="Delete Note"
        cancelText="Cancel"
        variant="destructive"
      />
    </div>
  )
}


'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type Flashcard } from '@/lib/api'

function collectTags(flashcards: Flashcard[]): string[] {
  const tags = new Set<string>()
  for (const flashcard of flashcards) {
    for (const tag of flashcard.tags ?? []) tags.add(tag)
  }
  return Array.from(tags).sort()
}

function matchesFilters(flashcard: Flashcard, query: string, selectedTags: string[]): boolean {
  if (query && !flashcard.question.toLowerCase().includes(query) && !flashcard.answer.toLowerCase().includes(query)) {
    return false
  }
  if (selectedTags.length > 0 && !selectedTags.some((tag) => flashcard.tags?.includes(tag))) {
    return false
  }
  return true
}

export function useFlashcardCollection(courseId?: string) {
  const [flashcards, setFlashcards] = useState<Flashcard[]>([])
  const [availableTags, setAvailableTags] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])

  const fetchFlashcards = useCallback(
    (tags: string[], search: string) => api.getUserFlashcards({ tags, search, courseId }),
    [courseId]
  )

  const reload = useCallback(async (tags: string[] = [], search: string = '') => {
    try {
      setLoading(true)
      const response = await fetchFlashcards(tags, search)
      setFlashcards(response)
      setAvailableTags(collectTags(response))
    } catch (error) {
      console.error('Failed to load flashcards:', error)
    } finally {
      setLoading(false)
    }
  }, [fetchFlashcards])

  useEffect(() => {
    reload()
  }, [reload])

  const search = useCallback(async () => {
    try {
      setLoading(true)
      setFlashcards(await fetchFlashcards(selectedTags, searchQuery))
    } catch (error) {
      console.error('Failed to search flashcards:', error)
    } finally {
      setLoading(false)
    }
  }, [fetchFlashcards, selectedTags, searchQuery])

  const filteredFlashcards = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    return flashcards.filter((flashcard) => matchesFilters(flashcard, query, selectedTags))
  }, [flashcards, searchQuery, selectedTags])

  const toggleTag = useCallback((tag: string) => {
    setSelectedTags((current) => (current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag]))
  }, [])

  const clearFilters = useCallback(() => {
    setSearchQuery('')
    setSelectedTags([])
  }, [])

  return {
    flashcards,
    filteredFlashcards,
    availableTags,
    loading,
    searchQuery,
    setSearchQuery,
    selectedTags,
    toggleTag,
    clearFilters,
    search,
    refresh: () => reload(selectedTags, searchQuery),
  }
}

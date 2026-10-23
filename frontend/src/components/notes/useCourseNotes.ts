'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, type Note } from '@/lib/api'

export function useCourseNotes(courseId: string) {
  const [notes, setNotes] = useState<Note[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      const response = await api.getNotes(courseId)
      setNotes(response.notes)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load notes')
    }
  }, [courseId])

  useEffect(() => {
    setNotes(null)
    reload()
  }, [reload])

  const upsert = useCallback((note: Note) => {
    setNotes((current) => {
      const list = current ?? []
      return list.some((existing) => existing.id === note.id)
        ? list.map((existing) => (existing.id === note.id ? note : existing))
        : [note, ...list]
    })
  }, [])

  const remove = useCallback(async (noteId: string) => {
    await api.deleteNote(noteId)
    setNotes((current) => (current ?? []).filter((note) => note.id !== noteId))
  }, [])

  return { notes, error, reload, upsert, remove }
}

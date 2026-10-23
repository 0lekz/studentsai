'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Plus } from 'lucide-react'
import type { Note } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { ToastAction } from '@/components/ui/toast'
import { EditableNoteView } from './EditableNoteView'
import { KeyboardShortcuts } from './KeyboardShortcuts'
import { NotesList } from './NotesList'
import { useCourseNotes } from './useCourseNotes'

export function NotesWorkspace({ courseId }: { courseId: string }) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const { notes, error, upsert, remove } = useCourseNotes(courseId)
  const urlNoteId = searchParams.get('note')
  const [selectedId, setSelectedId] = useState(urlNoteId)
  const [syncedUrlNoteId, setSyncedUrlNoteId] = useState(urlNoteId)
  const [composing, setComposing] = useState(false)
  const [showList, setShowList] = useState(true)
  const [showShortcuts, setShowShortcuts] = useState(false)

  if (urlNoteId !== syncedUrlNoteId) {
    setSyncedUrlNoteId(urlNoteId)
    if (urlNoteId !== selectedId) {
      setSelectedId(urlNoteId)
      if (urlNoteId) setComposing(false)
    }
  }

  const selectedNote = selectedId ? notes?.find((note) => note.id === selectedId) : undefined
  const editorOpen = Boolean(selectedNote) || composing

  const selectNote = useCallback(
    (noteId: string | null) => {
      setSelectedId(noteId)
      setComposing(false)
      router.replace(noteId ? `${pathname}?note=${noteId}` : pathname, { scroll: false })
    },
    [router, pathname]
  )

  const startNewNote = useCallback(() => {
    setSelectedId(null)
    setComposing(true)
    router.replace(pathname, { scroll: false })
  }, [router, pathname])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey)) return
      const typingInEditor = event.target instanceof HTMLElement && event.target.isContentEditable
      if (event.key === 'k' && !typingInEditor) {
        event.preventDefault()
        document.querySelector<HTMLInputElement>('input[aria-label="Search notes"]')?.focus()
      } else if (event.key === 'n') {
        event.preventDefault()
        startNewNote()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [startNewNote])

  const handleSave = (note: Note) => {
    upsert(note)
    if (note.id !== selectedId) selectNote(note.id)
  }

  const handleDelete = async (noteId: string) => {
    try {
      await remove(noteId)
      if (noteId === selectedId) selectNote(null)
    } catch (deleteError) {
      toast({ title: 'Could not delete the note', description: deleteError instanceof Error ? deleteError.message : undefined, variant: 'destructive' })
    }
  }

  const navigateToTitle = (title: string) => {
    const target = notes?.find((note) => note.title.toLowerCase() === title.toLowerCase())
    if (target) selectNote(target.id)
  }

  const announceFlashcards = (count: number) => {
    toast({
      title: `Made ${pluralize(count, 'flashcard')}`,
      description: 'Study them in Practice.',
      action: (
        <ToastAction altText="Open Practice" asChild>
          <Link href={`/courses/${courseId}/practice`}>Practice</Link>
        </ToastAction>
      ),
    })
  }

  if (error) {
    return (
      <div className="p-gutter">
        <Alert variant="error">{error}</Alert>
      </div>
    )
  }

  if (!notes) return <Spinner className="flex-1" label="Loading notes" />

  return (
    <div className="flex min-h-0 flex-1">
      {showList && (
        <aside
          className={cn(
            'min-h-0 w-full flex-col border-r border-border bg-surface md:flex md:w-80 md:shrink-0',
            editorOpen ? 'hidden' : 'flex'
          )}
        >
          <div className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-border px-3">
            <h2 className="text-body font-semibold text-foreground">
              Notes <span className="font-normal text-muted-foreground">{notes.length}</span>
            </h2>
            <Button size="sm" onClick={startNewNote}>
              <Plus className="h-4 w-4" />
              New note
            </Button>
          </div>
          <div className="min-h-0 flex-1">
            <NotesList
              notes={notes}
              onEdit={(note) => selectNote(note.id)}
              onSelect={(note) => selectNote(note.id)}
              onDelete={handleDelete}
              selectedNoteId={selectedNote?.id}
            />
          </div>
        </aside>
      )}

      <section className={cn('min-h-0 min-w-0 flex-1 flex-col md:flex', editorOpen || !showList ? 'flex' : 'hidden')}>
        <EditableNoteView
          note={selectedNote}
          courseId={courseId}
          onSave={handleSave}
          onNavigateByTitle={navigateToTitle}
          showNotesPanel={showList}
          onToggleNotesPanel={() => setShowList((visible) => !visible)}
          onCreateNew={startNewNote}
          onBack={() => selectNote(null)}
          onShowShortcuts={() => setShowShortcuts(true)}
          onFlashcardsCreated={announceFlashcards}
        />
      </section>

      <KeyboardShortcuts isOpen={showShortcuts} onClose={() => setShowShortcuts(false)} />
    </div>
  )
}

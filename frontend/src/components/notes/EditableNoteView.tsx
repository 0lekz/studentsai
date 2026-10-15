'use client'

import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Focus, HelpCircle, Layers, Loader2, PanelLeftClose, PanelLeftOpen, Plus, Save, Sparkles } from 'lucide-react'
import { api, type Note } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { WysiwygEditor } from './WysiwygEditor'
import { DistractionFreeMode } from './DistractionFreeMode'

const AUTOSAVE_DELAY_MS = 3000
const SAVED_FLASH_MS = 3000

interface EditableNoteViewProps {
  note?: Note
  courseId?: string
  onSave: (note: Note) => void
  onNavigateByTitle?: (title: string) => void
  showNotesPanel?: boolean
  onToggleNotesPanel?: () => void
  onCreateNew?: () => void
  onBack?: () => void
  onShowShortcuts?: () => void
  onFlashcardsCreated?: (count: number) => void
}

function countWords(htmlContent: string): number {
  const text = htmlContent.replace(/<[^>]*>/g, '').trim()
  return text ? text.split(/\s+/).length : 0
}

export function EditableNoteView({
  note,
  courseId,
  onSave,
  onNavigateByTitle,
  showNotesPanel,
  onToggleNotesPanel,
  onCreateNew,
  onBack,
  onShowShortcuts,
  onFlashcardsCreated,
}: EditableNoteViewProps) {
  const { toast } = useToast()
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [loading, setLoading] = useState(false)
  const [summarizing, setSummarizing] = useState(false)
  const [generatingCards, setGeneratingCards] = useState(false)
  const [error, setError] = useState('')
  const [autoSaving, setAutoSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [showSaveTime, setShowSaveTime] = useState(false)
  const [showDistractionFree, setShowDistractionFree] = useState(false)
  const [syncedNoteId, setSyncedNoteId] = useState(note?.id)
  const [editorSession, setEditorSession] = useState(0)

  const noteId = note?.id
  const isExistingNote = !!note
  const autoSaveTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined)
  const autoSaveRef = useRef<() => void>(() => {})

  if (noteId !== syncedNoteId) {
    const justCreated = syncedNoteId === undefined && lastSaved !== null
    setSyncedNoteId(noteId)
    setTitle(note?.title || '')
    setContent(note?.content || '')
    setHasUnsavedChanges(false)
    if (!justCreated) {
      setLastSaved(null)
      setEditorSession((session) => session + 1)
    }
    setError('')
  }

  useEffect(() => {
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }
  }, [noteId])

  useEffect(() => {
    if (note) {
      setHasUnsavedChanges(title !== note.title || content !== note.content)
    } else {
      setHasUnsavedChanges(title.trim() !== '' || content.trim() !== '')
    }
  }, [title, content, note])

  const flashSaved = () => {
    setLastSaved(new Date())
    setHasUnsavedChanges(false)
    setShowSaveTime(true)
    setTimeout(() => setShowSaveTime(false), SAVED_FLASH_MS)
  }

  const performAutoSave = async () => {
    if (!hasUnsavedChanges || !title.trim() || !content.trim()) return
    setAutoSaving(true)
    try {
      const savedNote = note ? await api.updateNote(note.id, { title, content }) : await api.createNote(title, content, courseId)
      flashSaved()
      onSave(savedNote)
    } catch (err) {
      console.error('Auto-save failed:', err)
    } finally {
      setAutoSaving(false)
    }
  }

  useEffect(() => {
    autoSaveRef.current = performAutoSave
  })

  useEffect(() => {
    if (!hasUnsavedChanges) return
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }
    autoSaveTimeoutRef.current = setTimeout(() => autoSaveRef.current(), AUTOSAVE_DELAY_MS)
    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }
    }
  }, [title, content, isExistingNote, hasUnsavedChanges])

  const handleManualSave = async () => {
    if (!title.trim() || !content.trim()) {
      setError('Title and content are required')
      return
    }
    setLoading(true)
    setError('')
    try {
      const savedNote = note ? await api.updateNote(note.id, { title, content }) : await api.createNote(title, content, courseId)
      flashSaved()
      onSave(savedNote)
    } catch {
      setError('Failed to save note')
    } finally {
      setLoading(false)
    }
  }

  const handleSummarize = async () => {
    if (!note) return
    if (!content.trim()) {
      setError('Add some content to summarize')
      return
    }
    setSummarizing(true)
    setError('')
    try {
      onSave(await api.summarizeNote(note.id))
    } catch {
      setError('Failed to generate summary')
    } finally {
      setSummarizing(false)
    }
  }

  const handleMakeFlashcards = async () => {
    if (!note) return
    setGeneratingCards(true)
    setError('')
    try {
      const cards = await api.generateNoteFlashcards(note.id)
      onFlashcardsCreated?.(cards.length)
    } catch (generateError) {
      toast({
        title: 'Could not make flashcards',
        description: generateError instanceof Error ? generateError.message : undefined,
        variant: 'destructive',
      })
    } finally {
      setGeneratingCards(false)
    }
  }

  if (showDistractionFree) {
    return (
      <DistractionFreeMode
        note={note}
        courseId={courseId}
        onSave={(savedNote) => {
          onSave(savedNote)
          setTitle(savedNote.title)
          setContent(savedNote.content)
        }}
        onExit={() => setShowDistractionFree(false)}
        onNavigateByTitle={onNavigateByTitle}
      />
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <div className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-border px-2 md:px-4">
        <div className="flex min-w-0 items-center gap-1">
          {onBack && (
            <Button variant="ghost" size="icon-sm" onClick={onBack} aria-label="Back to notes" className="md:hidden">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          {onToggleNotesPanel && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onToggleNotesPanel}
              className="hidden text-muted-foreground md:inline-flex"
              aria-label={showNotesPanel ? 'Hide notes list' : 'Show notes list'}
              title={showNotesPanel ? 'Hide notes list' : 'Show notes list'}
            >
              {showNotesPanel ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
            </Button>
          )}
          <span className="ml-1 truncate text-body font-medium text-foreground">{isExistingNote ? 'Note' : 'New note'}</span>
          <SaveStatus
            autoSaving={autoSaving}
            hasUnsavedChanges={hasUnsavedChanges && isExistingNote}
            lastSaved={lastSaved}
            showSaveTime={showSaveTime}
          />
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDistractionFree(true)}
            className="text-muted-foreground"
            title="Distraction-free mode"
          >
            <Focus className="h-4 w-4" />
            <span className="hidden sm:inline">Focus</span>
          </Button>
          {onShowShortcuts && (
            <Button variant="ghost" size="icon-sm" onClick={onShowShortcuts} className="hidden text-muted-foreground md:inline-flex" aria-label="Keyboard shortcuts">
              <HelpCircle className="h-4 w-4" />
            </Button>
          )}
          {onCreateNew && isExistingNote && (
            <Button variant="ghost" size="icon-sm" onClick={onCreateNew} className="text-muted-foreground" aria-label="New note" title="New note">
              <Plus className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="error" className="mx-4 mt-4 md:mx-6">
          {error}
        </Alert>
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4 md:px-6 md:py-6">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Note title"
          aria-label="Note title"
          className="w-full border-0 border-b border-border bg-transparent pb-2 text-headline font-semibold text-foreground placeholder:text-muted-foreground focus:border-input focus:outline-none"
          spellCheck
          autoCorrect="on"
          autoCapitalize="words"
        />

        {note?.summary && (
          <div className="mt-4 rounded-control bg-muted px-4 py-3">
            <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">Summary</p>
            <p className="mt-1 whitespace-pre-wrap text-body text-foreground">{note.summary}</p>
          </div>
        )}

        <div className="mt-4 flex flex-1 flex-col">
          <div className="mb-2 flex items-center justify-end">
            <span className="text-caption text-muted-foreground">{countWords(content)} words</span>
          </div>
          <div className="flex-1">
            <WysiwygEditor
              key={editorSession}
              initialContent={content}
              onChange={setContent}
              placeholder="Start writing your notes here..."
              className="h-full overflow-y-auto"
              autoFocus={!isExistingNote}
            />
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <Button variant="outline" onClick={handleManualSave} disabled={loading || !title.trim() || !content.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {loading ? 'Saving...' : isExistingNote ? 'Save' : 'Create note'}
          </Button>
          {isExistingNote && (
            <>
              <Button variant="outline" onClick={handleSummarize} disabled={summarizing || !content.trim()}>
                {summarizing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {summarizing ? 'Summarizing...' : 'Summarize'}
              </Button>
              <Button variant="outline" onClick={handleMakeFlashcards} disabled={generatingCards || !content.trim()}>
                {generatingCards ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers className="h-4 w-4" />}
                {generatingCards ? 'Making flashcards...' : 'Make flashcards'}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

interface SaveStatusProps {
  autoSaving: boolean
  hasUnsavedChanges: boolean
  lastSaved: Date | null
  showSaveTime: boolean
}

function SaveStatus({ autoSaving, hasUnsavedChanges, lastSaved, showSaveTime }: SaveStatusProps) {
  if (autoSaving) {
    return (
      <span className="ml-2 flex items-center gap-1 text-caption text-brand-soft-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        Saving...
      </span>
    )
  }
  if (hasUnsavedChanges) {
    return (
      <span className="ml-2 flex items-center gap-1.5 text-caption text-brand-soft-foreground">
        <span className="h-2 w-2 rounded-full bg-brand" />
        Unsaved
      </span>
    )
  }
  if (lastSaved) {
    return (
      <span className="ml-2 flex items-center gap-1.5 text-caption text-success">
        <span className="h-2 w-2 rounded-full bg-success" />
        {showSaveTime ? `Saved ${lastSaved.toLocaleTimeString()}` : 'Saved'}
      </span>
    )
  }
  return null
}

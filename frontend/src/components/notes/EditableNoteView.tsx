'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api, type Note } from '@/lib/api'
import { Save, FileText, PanelLeftClose, PanelLeftOpen, Loader2, Plus, Focus } from 'lucide-react'
import { WysiwygEditor } from './WysiwygEditor'
import { DistractionFreeMode } from './DistractionFreeMode'

interface EditableNoteViewProps {
  note?: Note
  onSave: (note: Note) => void
  onNavigateByTitle?: (title: string) => void
  showNotesPanel?: boolean
  onToggleNotesPanel?: () => void
  onCreateNew?: () => void
}

export function EditableNoteView({ 
  note, 
  onSave, 
  onNavigateByTitle, 
  showNotesPanel, 
  onToggleNotesPanel,
  onCreateNew 
}: EditableNoteViewProps) {
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [loading, setLoading] = useState(false)
  const [summarizing, setSummarizing] = useState(false)
  const [error, setError] = useState('')
  const [autoSaving, setAutoSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [showSaveTime, setShowSaveTime] = useState(false)
  const [showDistractionFree, setShowDistractionFree] = useState(false)

  const isExistingNote = !!note
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout>(undefined)

  // Reset state when note changes
  useEffect(() => {
    if (note) {
      setTitle(note.title || '')
      setContent(note.content || '')
      setHasUnsavedChanges(false)
      setLastSaved(null)
      setError('')
    } else {
      setTitle('')
      setContent('')
      setHasUnsavedChanges(false)
      setLastSaved(null)
      setError('')
    }
  }, [note?.id]) // Only reset when note ID changes

  // Clear auto-save timeout when note changes
  useEffect(() => {
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }
  }, [note?.id])

  // Track changes
  useEffect(() => {
    if (isExistingNote) {
      const hasChanges = title !== note.title || content !== note.content
      setHasUnsavedChanges(hasChanges)
    } else {
      // For new notes, any content means unsaved changes
      const hasChanges = title.trim() !== '' || content.trim() !== ''
      setHasUnsavedChanges(hasChanges)
    }
  }, [title, content, note, isExistingNote])

  // Auto-save functionality for existing notes
  const performAutoSave = async () => {
    if (!isExistingNote || !hasUnsavedChanges) return
    if (!title.trim() || !content.trim()) return

    setAutoSaving(true)
    try {
      const savedNote = await api.updateNote(note.id, { title, content })
      setLastSaved(new Date())
      setHasUnsavedChanges(false)
      onSave(savedNote)
      // Show save time for 3 seconds
      setShowSaveTime(true)
      setTimeout(() => setShowSaveTime(false), 3000)
    } catch (err) {
      console.error('Auto-save failed:', err)
    } finally {
      setAutoSaving(false)
    }
  }

  // Auto-save functionality for new notes (create them)
  const performAutoSaveNew = async () => {
    if (isExistingNote || !hasUnsavedChanges) return
    if (!title.trim() || !content.trim()) return

    setAutoSaving(true)
    try {
      const savedNote = await api.createNote(title, content)
      setLastSaved(new Date())
      setHasUnsavedChanges(false)
      // Update the note reference to mark it as existing
      onSave(savedNote)
      // Show save time for 3 seconds
      setShowSaveTime(true)
      setTimeout(() => setShowSaveTime(false), 3000)
    } catch (err) {
      console.error('Auto-save failed:', err)
    } finally {
      setAutoSaving(false)
    }
  }

  // Debounced auto-save
  useEffect(() => {
    if (!hasUnsavedChanges) return

    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }

    autoSaveTimeoutRef.current = setTimeout(() => {
      if (isExistingNote) {
        performAutoSave()
      } else {
        performAutoSaveNew()
      }
    }, 3000)

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
      let savedNote: Note
      if (isExistingNote) {
        savedNote = await api.updateNote(note.id, { title, content })
      } else {
        savedNote = await api.createNote(title, content)
      }
      setLastSaved(new Date())
      setHasUnsavedChanges(false)
      onSave(savedNote)
      // Show save time for 3 seconds
      setShowSaveTime(true)
      setTimeout(() => setShowSaveTime(false), 3000)
    } catch {
      setError('Failed to save note')
    } finally {
      setLoading(false)
    }
  }

  const handleSummarize = async () => {
    if (!content.trim()) {
      setError('Add some content to summarize')
      return
    }

    setSummarizing(true)
    setError('')

    try {
      if (isExistingNote) {
        const updatedNote = await api.summarizeNote(note.id)
        onSave(updatedNote)
      } else {
        const result = await api.summarizeText(content)
        alert(`Summary: ${result.summary}`)
      }
    } catch {
      setError('Failed to generate summary')
    } finally {
      setSummarizing(false)
    }
  }

  const getWordCount = (htmlContent: string): number => {
    const text = htmlContent.replace(/<[^>]*>/g, '').trim()
    return text ? text.split(/\s+/).length : 0
  }

  const wordCount = getWordCount(content)

  // Show distraction-free mode
  if (showDistractionFree) {
    return (
      <DistractionFreeMode
        note={isExistingNote ? note : undefined}
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
    <div className="h-full flex flex-col bg-white dark:bg-[#141820]">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-3 dark:border-[#232a36]">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <FileText className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {isExistingNote ? 'Note' : 'New Note'}
            </span>
            
            {/* Auto-save status indicator */}
            {isExistingNote && (
              <div className="flex items-center space-x-2 text-xs">
                {autoSaving ? (
                  <div className="flex items-center space-x-1 text-orange-600 dark:text-orange-400">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Saving...</span>
                  </div>
                ) : hasUnsavedChanges ? (
                  <div className="flex items-center space-x-1 text-orange-600 dark:text-orange-400">
                    <div className="h-2 w-2 bg-orange-500 rounded-full"></div>
                    <span>Unsaved changes</span>
                  </div>
                ) : lastSaved ? (
                  <div className="flex items-center space-x-1 text-green-600 dark:text-green-400">
                    <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                    <span>{showSaveTime ? `Saved ${lastSaved.toLocaleTimeString()}` : 'Saved'}</span>
                  </div>
                ) : null}
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Distraction-Free Mode Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDistractionFree(true)}
              className="h-8 px-2 text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
              title="Enter distraction-free mode (Cmd/Ctrl + Enter)"
            >
              <Focus className="h-4 w-4 mr-1" />
              Focus
            </Button>

            {/* Panel Toggle Button */}
            {onToggleNotesPanel && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleNotesPanel}
                className="h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
                title={showNotesPanel ? "Hide notes panel" : "Show notes panel"}
              >
                {showNotesPanel ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
              </Button>
            )}
            
            {/* Create New Note Button */}
            {onCreateNew && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onCreateNew}
                className="h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
                title="Create new note"
              >
                <Plus className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg dark:bg-red-950/30 dark:border-red-900/40">
          <p className="text-red-800 dark:text-red-200 text-sm">{error}</p>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-y-auto p-6">
        {/* Title Input */}
        <div className="mb-6">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Note title..."
            className="text-2xl font-semibold border-0 border-b border-gray-200 rounded-none px-0 py-2 focus:ring-0 focus:border-gray-400 dark:bg-[#141820] dark:text-gray-100 dark:border-[#232a36] dark:placeholder:text-gray-500 dark:focus:border-gray-500"
            spellCheck={true}
            autoCorrect="on"
            autoCapitalize="words"
            style={{
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
            }}
          />
        </div>

        {/* WYSIWYG Editor */}
        <div className="flex-1 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <span className="text-sm text-gray-500 dark:text-gray-400">Content</span>
            <span className="text-sm text-gray-500 dark:text-gray-400">{wordCount} words</span>
          </div>
          
          <div className="flex-1 min-h-0 overflow-hidden">
            <WysiwygEditor
              content={content}
              onChange={setContent}
              placeholder="Start writing your notes here..."
              className="h-full overflow-y-auto"
              autoFocus={!isExistingNote}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-[#232a36] mt-6">
          <div className="flex gap-2">
            <Button
              onClick={handleManualSave}
              disabled={loading || !title.trim() || !content.trim()}
              className="bg-orange-500 hover:bg-orange-600 text-white dark:bg-orange-500 dark:hover:bg-orange-400 dark:text-white"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  {isExistingNote ? 'Update Note' : 'Create Note'}
                </>
              )}
            </Button>
            
            {isExistingNote && (
              <Button
                onClick={handleSummarize}
                disabled={summarizing || !content.trim()}
                variant="outline"
                className="border-gray-200 text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:bg-[#0f1318] dark:hover:bg-[#1d2430]"
              >
                {summarizing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Summarizing...
                  </>
                ) : (
                  'AI Summary'
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

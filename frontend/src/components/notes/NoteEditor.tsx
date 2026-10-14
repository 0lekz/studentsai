'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api, type Note } from '@/lib/api'
import { Save, FileText, X, PanelLeftClose, PanelLeftOpen, Loader2 } from 'lucide-react'
import { WysiwygEditor } from './WysiwygEditor'

interface NoteEditorProps {
  note?: Note
  onSave: (note: Note) => void
  onCancel: () => void
  onNavigateByTitle?: (title: string) => void
  showNotesPanel?: boolean
  onToggleNotesPanel?: () => void
}

export function NoteEditor({ note, onSave, onCancel, showNotesPanel, onToggleNotesPanel }: NoteEditorProps) {
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [loading, setLoading] = useState(false)
  const [summarizing, setSummarizing] = useState(false)
  const [error, setError] = useState('')
  const [autoSaving, setAutoSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  const isEditing = !!note
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout>(undefined)

  // Track changes
  useEffect(() => {
    if (isEditing) {
      const hasChanges = title !== note.title || content !== note.content
      setHasUnsavedChanges(hasChanges)
    }
  }, [title, content, note, isEditing])

  // Auto-save functionality with better UX
  const performAutoSave = async () => {
    if (!isEditing || !hasUnsavedChanges) return
    if (!title.trim() || !content.trim()) return

    setAutoSaving(true)
    try {
      const savedNote = await api.updateNote(note.id, { title, content })
      setLastSaved(new Date())
      setHasUnsavedChanges(false)
      // Update the parent without changing the view - this is key!
      onSave(savedNote)
    } catch (err) {
      console.error('Auto-save failed:', err)
    } finally {
      setAutoSaving(false)
    }
  }

  // Debounced auto-save
  useEffect(() => {
    if (!isEditing || !hasUnsavedChanges) return

    // Clear existing timeout
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }

    // Set new timeout
    autoSaveTimeoutRef.current = setTimeout(() => {
      performAutoSave()
    }, 3000)

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }
    }
  }, [title, content, isEditing, hasUnsavedChanges])

  const handleManualSave = async () => {
    if (!title.trim() || !content.trim()) {
      setError('Title and content are required')
      return
    }

    setLoading(true)
    setError('')

    try {
      let savedNote: Note
      if (isEditing) {
        savedNote = await api.updateNote(note.id, { title, content })
      } else {
        savedNote = await api.createNote(title, content)
      }
      setLastSaved(new Date())
      setHasUnsavedChanges(false)
      onSave(savedNote)
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
      if (isEditing) {
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
    // Strip HTML and count words
    const text = htmlContent.replace(/<[^>]*>/g, '').trim()
    return text ? text.split(/\s+/).length : 0
  }

  const wordCount = getWordCount(content)

  return (
    <div className="h-full flex flex-col bg-white dark:bg-[#141820]">
      {/* Editor Header */}
      <div className="border-b border-gray-200 px-6 py-3 dark:border-[#232a36]">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <FileText className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {isEditing ? 'Edit Note' : 'Create New Note'}
            </span>
            
            {/* Auto-save status indicator */}
            {isEditing && (
              <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                {autoSaving ? (
                  <>
                    <Loader2 className="h-3 w-3 animate-spin text-orange-500" />
                    <span>Saving...</span>
                  </>
                ) : hasUnsavedChanges ? (
                  <span className="text-orange-600 dark:text-orange-400">Unsaved changes</span>
                ) : lastSaved ? (
                  <span className="text-green-600 dark:text-green-400">
                    Saved {lastSaved.toLocaleTimeString()}
                  </span>
                ) : null}
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
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
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              className="h-8 w-8 p-0 dark:text-gray-300 dark:hover:bg-[#0f1115]"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg dark:bg-red-950/30 dark:border-red-900/40">
          <p className="text-red-800 dark:text-red-200 text-sm">{error}</p>
        </div>
      )}

      {/* Editor Content */}
      <div className="flex-1 flex flex-col overflow-hidden p-6">
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
              autoFocus={!isEditing} // Auto-focus for new notes
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
                  {isEditing ? 'Update Note' : 'Create Note'}
                </>
              )}
            </Button>
            
            {isEditing && (
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

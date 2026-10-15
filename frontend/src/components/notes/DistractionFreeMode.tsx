'use client'

import { useState, useEffect, useRef } from 'react'
import { Focus, Loader2, Maximize2, Minimize2, Moon, Save, Settings, Sun, X } from 'lucide-react'
import { api, type Note } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { WysiwygEditor } from './WysiwygEditor'

const AUTOSAVE_DELAY_MS = 3000

interface DistractionFreeModeProps {
  note?: Note
  courseId?: string
  onSave: (note: Note) => void
  onExit: () => void
  onNavigateByTitle?: (title: string) => void
}

function readStored<T>(key: string, parse: (raw: string) => T, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  const saved = localStorage.getItem(key)
  return saved ? parse(saved) : fallback
}

function usePersistedSetting<T>(key: string, parse: (raw: string) => T, fallback: T) {
  const [value, setValue] = useState(() => readStored(key, parse, fallback))
  useEffect(() => {
    localStorage.setItem(key, String(value))
  }, [key, value])
  return [value, setValue] as const
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

function countWords(htmlContent: string): number {
  const text = htmlContent.replace(/<[^>]*>/g, '').trim()
  return text ? text.split(/\s+/).length : 0
}

export function DistractionFreeMode({ note, courseId, onSave, onExit }: DistractionFreeModeProps) {
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window === 'undefined') return false
    return document.documentElement.classList.contains('dark') || window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const [showSettings, setShowSettings] = useState(false)
  const [fontSize, setFontSize] = usePersistedSetting('focusedMode_fontSize', (raw) => parseInt(raw), 16)
  const [lineHeight, setLineHeight] = usePersistedSetting('focusedMode_lineHeight', parseFloat, 1.6)
  const [maxWidth, setMaxWidth] = usePersistedSetting('focusedMode_maxWidth', (raw) => parseInt(raw), 800)
  const [showWordCount, setShowWordCount] = usePersistedSetting('focusedMode_showWordCount', (raw) => raw === 'true', true)
  const [autoSave, setAutoSave] = usePersistedSetting('focusedMode_autoSave', (raw) => raw === 'true', true)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const handleSaveRef = useRef<() => Promise<void>>(async () => {})

  const isExistingNote = !!note

  const noteId = note?.id
  const autoSaveRef = useRef<() => Promise<void>>(async () => {})

  const performAutoSave = async () => {
    if (!note || (title === note.title && content === note.content)) return
    setIsSaving(true)
    try {
      const savedNote = await api.updateNote(note.id, { title, content })
      setLastSaved(new Date())
      onSave(savedNote)
    } catch (err) {
      console.error('Auto-save failed:', err)
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    autoSaveRef.current = performAutoSave
  })

  useEffect(() => {
    if (!noteId || !autoSave || !title.trim() || !content.trim()) return
    const timeoutId = setTimeout(() => autoSaveRef.current(), AUTOSAVE_DELAY_MS)
    return () => clearTimeout(timeoutId)
  }, [title, content, noteId, autoSave])

  const handleSave = async () => {
    if (!title.trim() || !content.trim()) return

    setIsSaving(true)
    try {
      const savedNote = note ? await api.updateNote(note.id, { title, content }) : await api.createNote(title, content, courseId)
      setLastSaved(new Date())
      onSave(savedNote)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    handleSaveRef.current = handleSave
  })

  const saveAndExit = () => {
    handleSaveRef.current().finally(onExit)
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        handleSaveRef.current()
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        handleSaveRef.current().finally(onExit)
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        toggleFullscreen()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onExit])

  useEffect(() => {
    const handleFullscreenChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  return (
    <div className={cn('fixed inset-0 z-50', isDarkMode ? 'dark' : 'light')}>
      <div className="flex h-full w-full flex-col bg-background text-foreground transition-colors">
        <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-4">
          <div className="flex min-w-0 items-center gap-3">
            <Focus className="h-5 w-5 shrink-0 text-brand" />
            <span className="hidden truncate font-medium sm:inline">Focus mode</span>
            {isExistingNote && autoSave && (
              <span className="text-caption">
                {isSaving ? (
                  <span className="text-brand-soft-foreground">Saving...</span>
                ) : lastSaved ? (
                  <span className="text-success">Saved {lastSaved.toLocaleTimeString()}</span>
                ) : null}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {showWordCount && <span className="mr-2 hidden text-body text-muted-foreground sm:inline">{countWords(content)} words</span>}
            <Button variant="ghost" size="icon-sm" onClick={() => setShowSettings(!showSettings)} aria-label="Writing settings" aria-pressed={showSettings}>
              <Settings className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={() => setIsDarkMode(!isDarkMode)} aria-label={isDarkMode ? 'Light background' : 'Dark background'}>
              {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={toggleFullscreen} aria-label={isFullscreen ? 'Exit full screen' : 'Full screen'}>
              {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
            <Button size="sm" onClick={() => handleSave()} disabled={isSaving || !title.trim() || !content.trim()} className="h-8">
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={saveAndExit} aria-label="Exit focus mode">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {showSettings && (
          <div className="absolute right-4 top-12 z-10 w-64 rounded-card border border-border bg-popover p-4 text-popover-foreground shadow-lg">
            <div className="space-y-4">
              <h3 className="font-medium">Writing settings</h3>
              <label className="block">
                <span className="text-body font-medium">Font size</span>
                <input type="range" min="12" max="24" value={fontSize} onChange={(e) => setFontSize(Number(e.target.value))} className="mt-1 w-full accent-[hsl(var(--primary))]" />
                <span className="text-caption text-muted-foreground">{fontSize}px</span>
              </label>
              <label className="block">
                <span className="text-body font-medium">Line height</span>
                <input type="range" min="1.2" max="2.0" step="0.1" value={lineHeight} onChange={(e) => setLineHeight(Number(e.target.value))} className="mt-1 w-full accent-[hsl(var(--primary))]" />
                <span className="text-caption text-muted-foreground">{lineHeight}</span>
              </label>
              <label className="block">
                <span className="text-body font-medium">Max width</span>
                <input type="range" min="600" max="1200" step="50" value={maxWidth} onChange={(e) => setMaxWidth(Number(e.target.value))} className="mt-1 w-full accent-[hsl(var(--primary))]" />
                <span className="text-caption text-muted-foreground">{maxWidth}px</span>
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-body">
                  <input type="checkbox" checked={showWordCount} onChange={(e) => setShowWordCount(e.target.checked)} className="rounded accent-[hsl(var(--primary))]" />
                  Show word count
                </label>
                <label className="flex items-center gap-2 text-body">
                  <input type="checkbox" checked={autoSave} onChange={(e) => setAutoSave(e.target.checked)} className="rounded accent-[hsl(var(--primary))]" />
                  Auto-save
                </label>
              </div>
            </div>
          </div>
        )}

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <div className="mx-auto w-full px-4 py-6 sm:px-8" style={{ maxWidth: `${maxWidth}px` }}>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Note title"
              aria-label="Note title"
              className="w-full border-0 border-b border-border bg-transparent pb-3 text-display font-semibold text-foreground placeholder:text-muted-foreground focus:border-input focus:outline-none"
            />
          </div>
          <div className="flex-1 px-4 pb-8 sm:px-8">
            <div className="mx-auto h-full" style={{ maxWidth: `${maxWidth}px` }}>
              <WysiwygEditor initialContent={content} onChange={setContent} placeholder="Start writing your notes here..." className="h-full" autoFocus />
            </div>
          </div>
        </div>

        <style jsx global>{`
          .ProseMirror {
            font-size: ${fontSize}px !important;
            line-height: ${lineHeight} !important;
          }

          .ProseMirror p.is-editor-empty:first-child::before {
            font-size: ${fontSize}px !important;
            line-height: ${lineHeight} !important;
          }
        `}</style>
      </div>
    </div>
  )
}

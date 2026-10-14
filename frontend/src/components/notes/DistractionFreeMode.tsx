'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { WysiwygEditor } from './WysiwygEditor'
import { 
  Minimize2, 
  Maximize2, 
  Moon, 
  Sun, 
  Focus,
  Save,
  X,
  Settings
} from 'lucide-react'
import { api, type Note } from '@/lib/api'

interface DistractionFreeModeProps {
  note?: Note
  onSave: (note: Note) => void
  onExit: () => void
  onNavigateByTitle?: (title: string) => void
}

export function DistractionFreeMode({ 
  note, 
  onSave, 
  onExit
}: DistractionFreeModeProps) {
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Detect current theme from document
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark') || 
             window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  })
  const [showSettings, setShowSettings] = useState(false)
  const [fontSize, setFontSize] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('focusedMode_fontSize')
      return saved ? parseInt(saved) : 16
    }
    return 16
  })
  const [lineHeight, setLineHeight] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('focusedMode_lineHeight')
      return saved ? parseFloat(saved) : 1.6
    }
    return 1.6
  })
  const [maxWidth, setMaxWidth] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('focusedMode_maxWidth')
      return saved ? parseInt(saved) : 800
    }
    return 800
  })
  const [showWordCount, setShowWordCount] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('focusedMode_showWordCount')
      return saved ? saved === 'true' : true
    }
    return true
  })
  const [autoSave, setAutoSave] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('focusedMode_autoSave')
      return saved ? saved === 'true' : true
    }
    return true
  })
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const isExistingNote = !!note

  // Save settings to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('focusedMode_fontSize', fontSize.toString())
    }
  }, [fontSize])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('focusedMode_lineHeight', lineHeight.toString())
    }
  }, [lineHeight])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('focusedMode_maxWidth', maxWidth.toString())
    }
  }, [maxWidth])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('focusedMode_showWordCount', showWordCount.toString())
    }
  }, [showWordCount])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('focusedMode_autoSave', autoSave.toString())
    }
  }, [autoSave])

  // Auto-save functionality
  useEffect(() => {
    if (!isExistingNote || !autoSave || !title.trim() || !content.trim()) return

    const timeoutId = setTimeout(async () => {
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
    }, 3000)

    return () => clearTimeout(timeoutId)
  }, [title, content, isExistingNote, autoSave, note?.id, onSave])

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  // Toggle dark mode
  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode)
  }

  // Manual save
  const handleSave = async () => {
    if (!title.trim() || !content.trim()) return

    setIsSaving(true)
    try {
      let savedNote: Note
      if (isExistingNote) {
        savedNote = await api.updateNote(note.id, { title, content })
      } else {
        savedNote = await api.createNote(title, content)
      }
      setLastSaved(new Date())
      onSave(savedNote)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setIsSaving(false)
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + S to save
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
      // Escape to exit (save first)
      if (e.key === 'Escape') {
        e.preventDefault()
        handleSave().then(() => {
          onExit()
        }).catch(() => {
          // Even if save fails, exit to prevent data loss
          onExit()
        })
      }
      // Cmd/Ctrl + Enter to toggle fullscreen
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        toggleFullscreen()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleSave, onExit])

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const getWordCount = (htmlContent: string): number => {
    const text = htmlContent.replace(/<[^>]*>/g, '').trim()
    return text ? text.split(/\s+/).length : 0
  }

  const wordCount = getWordCount(content)

  return (
    <div className={`fixed inset-0 z-50 ${isDarkMode ? 'dark' : ''}`}>
      <div className={`h-full w-full ${isDarkMode ? 'bg-[#0f1115]' : 'bg-gray-50'} transition-colors`}>
        {/* Top Bar */}
        <div className={`h-12 border-b ${isDarkMode ? 'border-[#232a36] bg-[#0f1115]' : 'border-gray-200 bg-gray-50'} flex items-center justify-between px-4`}>
          <div className="flex items-center space-x-3">
            <Focus className="h-5 w-5 text-orange-500" />
            <span className="font-medium text-gray-900 dark:text-gray-100">Distraction-Free Mode</span>
            
            {/* Auto-save indicator */}
            {isExistingNote && autoSave && (
              <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                {isSaving ? (
                  <span className="text-orange-600 dark:text-orange-400">Saving...</span>
                ) : lastSaved ? (
                  <span className="text-green-600 dark:text-green-400">
                    Saved {lastSaved.toLocaleTimeString()}
                  </span>
                ) : null}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {/* Word Count */}
            {showWordCount && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {wordCount} words
              </span>
            )}

            {/* Settings */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSettings(!showSettings)}
              className="h-8 w-8 p-0"
            >
              <Settings className="h-4 w-4" />
            </Button>

            {/* Dark Mode Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleDarkMode}
              className="h-8 w-8 p-0"
            >
              {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>

            {/* Fullscreen Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleFullscreen}
              className="h-8 w-8 p-0"
            >
              {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>

            {/* Save Button */}
            <Button
              onClick={handleSave}
              disabled={isSaving || !title.trim() || !content.trim()}
              className="h-8 px-3 bg-orange-500 hover:bg-orange-600 text-white"
            >
              {isSaving ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <>
                  <Save className="h-4 w-4 mr-1" />
                  Save
                </>
              )}
            </Button>

            {/* Exit Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                handleSave().then(() => {
                  onExit()
                }).catch(() => {
                  // Even if save fails, exit to prevent data loss
                  onExit()
                })
              }}
              className="h-8 w-8 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className={`absolute top-12 right-4 z-10 w-64 p-4 rounded-lg shadow-lg border ${isDarkMode ? 'bg-[#0f1115] border-[#232a36]' : 'bg-white border-gray-200'}`}>
            <div className="space-y-4">
              <h3 className="font-medium text-gray-900 dark:text-gray-100">Writing Settings</h3>
              
              {/* Font Size */}
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Font Size</label>
                <input
                  type="range"
                  min="12"
                  max="24"
                  value={fontSize}
                  onChange={(e) => setFontSize(Number(e.target.value))}
                  className="w-full mt-1"
                />
                <span className="text-xs text-gray-500 dark:text-gray-400">{fontSize}px</span>
              </div>

              {/* Line Height */}
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Line Height</label>
                <input
                  type="range"
                  min="1.2"
                  max="2.0"
                  step="0.1"
                  value={lineHeight}
                  onChange={(e) => setLineHeight(Number(e.target.value))}
                  className="w-full mt-1"
                />
                <span className="text-xs text-gray-500 dark:text-gray-400">{lineHeight}</span>
              </div>

              {/* Max Width */}
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Max Width</label>
                <input
                  type="range"
                  min="600"
                  max="1200"
                  step="50"
                  value={maxWidth}
                  onChange={(e) => setMaxWidth(Number(e.target.value))}
                  className="w-full mt-1"
                />
                <span className="text-xs text-gray-500 dark:text-gray-400">{maxWidth}px</span>
              </div>

              {/* Toggles */}
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={showWordCount}
                    onChange={(e) => setShowWordCount(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">Show word count</span>
                </label>
                
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={autoSave}
                    onChange={(e) => setAutoSave(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">Auto-save</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="h-[calc(100%-3rem)] flex flex-col">
          {/* Title Input */}
          <div className="px-8 py-6">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Note title..."
              className={`text-3xl font-semibold border-0 border-b rounded-none px-0 py-3 focus:ring-0 ${
                isDarkMode 
                  ? 'bg-[#0f1115] text-gray-100 border-[#232a36] focus:border-gray-500' 
                  : 'bg-gray-50 text-gray-900 border-gray-200 focus:border-gray-400'
              }`}
              style={{
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
                fontSize: '2rem',
                lineHeight: '1.2'
              }}
            />
          </div>

          {/* Editor */}
          <div className="flex-1 px-8 pb-8">
            <div 
              className="h-full"
              style={{ 
                maxWidth: `${maxWidth}px`,
                margin: '0 auto'
              }}
            >
              <WysiwygEditor
                content={content}
                onChange={setContent}
                placeholder="Start writing your notes here..."
                className="h-full"
                autoFocus={true}
              />
            </div>
          </div>
        </div>

        {/* Custom styles for distraction-free mode */}
        <style jsx global>{`
          .ProseMirror {
            font-size: ${fontSize}px !important;
            line-height: ${lineHeight} !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
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

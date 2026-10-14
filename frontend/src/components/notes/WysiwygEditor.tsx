'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Typography from '@tiptap/extension-typography'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import { useEffect, useCallback, useState } from 'react'
import { Button } from '@/components/ui/button'
import { 
  Bold, 
  Italic, 
  Strikethrough, 
  List, 
  ListOrdered, 
  Quote, 
  Code, 
  Link as LinkIcon,
  Heading1,
  Heading2,
  Heading3,
  Minus,
  Undo,
  Redo,
  X
} from 'lucide-react'

interface WysiwygEditorProps {
  content: string
  onChange: (content: string) => void
  placeholder?: string
  className?: string
  autoFocus?: boolean
}

export function WysiwygEditor({ 
  content, 
  onChange, 
  placeholder = "Start writing...", 
  className = "",
  autoFocus = false 
}: WysiwygEditorProps) {
  const [showLinkDialog, setShowLinkDialog] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')
  
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable code blocks for now as they might interfere with markdown
        codeBlock: false,
        // Disable link since we're adding it separately
        link: false,
      }),
      Placeholder.configure({
        placeholder,
      }),
      Typography,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-orange-600 underline hover:text-orange-700 dark:text-orange-400 dark:hover:text-orange-300 transition-colors',
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: 'max-w-full rounded-lg shadow-md border border-gray-200 dark:border-gray-600 my-4',
        },
      }),
    ],
    content,
    onUpdate: ({ editor }) => {
      // Get HTML content and convert to markdown-like format if needed
      const html = editor.getHTML()
      onChange(html)
    },
    editorProps: {
      attributes: {
        class: `prose prose-orange max-w-none dark:prose-invert prose-lg focus:outline-none ${className}`,
        style: `
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          line-height: 1.6;
          font-size: 16px;
          min-height: 200px;
          max-height: 70vh;
          overflow-y: auto;
          padding: 1rem;
        `,
        spellcheck: 'true',
        autocorrect: 'on',
        autocapitalize: 'sentences',
      },
    },
  })

  // Update editor content when prop changes
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content, { emitUpdate: true })
    }
  }, [content, editor])

  // Auto-focus if requested
  useEffect(() => {
    if (editor && autoFocus) {
      editor.commands.focus()
    }
  }, [editor, autoFocus])

  // Handle paste events for images
  const handlePaste = useCallback(async (event: ClipboardEvent) => {
    if (!editor) return

    const items = event.clipboardData?.items
    if (!items) return

    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        event.preventDefault()
        const file = item.getAsFile()
        if (!file) continue

        try {
          // You can integrate your existing image upload API here
          const formData = new FormData()
          formData.append('file', file)
          
          // For now, we'll use a placeholder - you can replace this with your actual API call
          // const response = await api.uploadImage(file)
          // editor.commands.setImage({ src: response.url })
          
          // Placeholder implementation
          const reader = new FileReader()
          reader.onload = (e) => {
            if (e.target?.result) {
              editor.commands.setImage({ src: e.target.result as string })
            }
          }
          reader.readAsDataURL(file)
        } catch (error) {
          console.error('Failed to upload image:', error)
        }
      }
    }
  }, [editor])

  useEffect(() => {
    const editorElement = editor?.view?.dom
    if (editorElement) {
      editorElement.addEventListener('paste', handlePaste)
      return () => editorElement.removeEventListener('paste', handlePaste)
    }
  }, [editor, handlePaste])

  // Keyboard shortcuts
  useEffect(() => {
    if (!editor) return

    const handleKeyDown = (event: KeyboardEvent) => {
      // Bold: Cmd/Ctrl + B
      if ((event.metaKey || event.ctrlKey) && event.key === 'b') {
        event.preventDefault()
        editor.chain().focus().toggleBold().run()
      }
      // Italic: Cmd/Ctrl + I
      if ((event.metaKey || event.ctrlKey) && event.key === 'i') {
        event.preventDefault()
        editor.chain().focus().toggleItalic().run()
      }
      // Code: Cmd/Ctrl + E
      if ((event.metaKey || event.ctrlKey) && event.key === 'e') {
        event.preventDefault()
        editor.chain().focus().toggleCode().run()
      }
      // Link: Cmd/Ctrl + K
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault()
        setShowLinkDialog(true)
      }
      // Heading 1: Cmd/Ctrl + 1
      if ((event.metaKey || event.ctrlKey) && event.key === '1') {
        event.preventDefault()
        editor.chain().focus().toggleHeading({ level: 1 }).run()
      }
      // Heading 2: Cmd/Ctrl + 2
      if ((event.metaKey || event.ctrlKey) && event.key === '2') {
        event.preventDefault()
        editor.chain().focus().toggleHeading({ level: 2 }).run()
      }
      // Heading 3: Cmd/Ctrl + 3
      if ((event.metaKey || event.ctrlKey) && event.key === '3') {
        event.preventDefault()
        editor.chain().focus().toggleHeading({ level: 3 }).run()
      }
      // Bullet List: Cmd/Ctrl + Shift + 8
      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key === '8') {
        event.preventDefault()
        editor.chain().focus().toggleBulletList().run()
      }
      // Numbered List: Cmd/Ctrl + Shift + 7
      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key === '7') {
        event.preventDefault()
        editor.chain().focus().toggleOrderedList().run()
      }
      // Blockquote: Cmd/Ctrl + Shift + >
      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key === '>') {
        event.preventDefault()
        editor.chain().focus().toggleBlockquote().run()
      }
    }

    const editorElement = editor.view.dom
    editorElement.addEventListener('keydown', handleKeyDown)
    
    return () => {
      editorElement.removeEventListener('keydown', handleKeyDown)
    }
  }, [editor])

  const handleAddLink = () => {
    if (linkUrl.trim()) {
      editor?.chain().focus().setLink({ href: linkUrl }).run()
      setLinkUrl('')
      setShowLinkDialog(false)
    }
  }

  const handleRemoveLink = () => {
    editor?.chain().focus().unsetLink().run()
  }

  if (!editor) {
    return (
      <div className="animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-5/6"></div>
      </div>
    )
  }

  return (
    <div className="wysiwyg-editor">
      {/* Formatting Toolbar */}
      <div className="border border-gray-200 dark:border-[#232a36] rounded-t-lg bg-gray-50 dark:bg-[#0f1115] p-2 flex flex-wrap items-center gap-1">
        {/* Text Formatting */}
        <div className="flex items-center gap-1 border-r border-gray-300 dark:border-gray-600 pr-2 mr-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleBold().run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('bold') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Bold (Cmd/Ctrl + B)"
          >
            <Bold className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('italic') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Italic (Cmd/Ctrl + I)"
          >
            <Italic className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleStrike().run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('strike') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Strikethrough"
          >
            <Strikethrough className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleCode().run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('code') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Code (Cmd/Ctrl + E)"
          >
            <Code className="h-4 w-4" />
          </Button>
        </div>

        {/* Headings */}
        <div className="flex items-center gap-1 border-r border-gray-300 dark:border-gray-600 pr-2 mr-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('heading', { level: 1 }) ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Heading 1 (Cmd/Ctrl + 1)"
          >
            <Heading1 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('heading', { level: 2 }) ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Heading 2 (Cmd/Ctrl + 2)"
          >
            <Heading2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('heading', { level: 3 }) ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Heading 3 (Cmd/Ctrl + 3)"
          >
            <Heading3 className="h-4 w-4" />
          </Button>
        </div>

        {/* Lists */}
        <div className="flex items-center gap-1 border-r border-gray-300 dark:border-gray-600 pr-2 mr-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('bulletList') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Bullet List (Cmd/Ctrl + Shift + 8)"
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('orderedList') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Numbered List (Cmd/Ctrl + Shift + 7)"
          >
            <ListOrdered className="h-4 w-4" />
          </Button>
        </div>

        {/* Block Elements */}
        <div className="flex items-center gap-1 border-r border-gray-300 dark:border-gray-600 pr-2 mr-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('blockquote') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Quote (Cmd/Ctrl + Shift + >)"
          >
            <Quote className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().setHorizontalRule().run()}
            className="h-8 w-8 p-0"
            title="Horizontal Rule"
          >
            <Minus className="h-4 w-4" />
          </Button>
        </div>

        {/* Links and Images */}
        <div className="flex items-center gap-1 border-r border-gray-300 dark:border-gray-600 pr-2 mr-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLinkDialog(true)}
            className={`h-8 w-8 p-0 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 ${editor.isActive('link') ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : ''}`}
            title="Add Link (Cmd/Ctrl + K)"
          >
            <LinkIcon className="h-4 w-4" />
          </Button>
          {editor.isActive('link') && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveLink}
              className="h-8 w-8 p-0 text-red-600 hover:text-red-700 dark:text-red-400"
              title="Remove Link"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* History */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            className="h-8 w-8 p-0"
            title="Undo (Cmd/Ctrl + Z)"
          >
            <Undo className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            className="h-8 w-8 p-0"
            title="Redo (Cmd/Ctrl + Y)"
          >
            <Redo className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Link Dialog */}
      {showLinkDialog && (
        <div className="absolute top-12 left-4 z-50 bg-white dark:bg-[#141820] border border-gray-200 dark:border-[#232a36] rounded-lg shadow-lg p-4 min-w-80">
          <div className="space-y-3">
            <h3 className="font-medium text-gray-900 dark:text-gray-100">Add Link</h3>
            <input
              type="url"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 border border-gray-200 dark:border-[#232a36] rounded-md bg-white dark:bg-[#0f1115] text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleAddLink()
                } else if (e.key === 'Escape') {
                  setShowLinkDialog(false)
                  setLinkUrl('')
                }
              }}
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowLinkDialog(false)
                  setLinkUrl('')
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleAddLink}
                disabled={!linkUrl.trim()}
                className="bg-orange-500 hover:bg-orange-600 text-white"
              >
                Add Link
              </Button>
            </div>
          </div>
        </div>
      )}

      <EditorContent 
        editor={editor} 
        className="min-h-[300px] focus-within:ring-2 focus-within:ring-orange-500 focus-within:ring-opacity-50 rounded-b-lg transition-all border border-t-0 border-gray-200 dark:border-[#232a36]"
      />
      
      {/* Custom styles for the editor */}
      <style jsx global>{`
        .ProseMirror {
          outline: none;
        }
        
        .ProseMirror p.is-editor-empty:first-child::before {
          content: attr(data-placeholder);
          float: left;
          color: #9ca3af;
          pointer-events: none;
          height: 0;
        }
        
        .ProseMirror h1 {
          font-size: 2.25rem;
          font-weight: 700;
          margin-bottom: 1.5rem;
          margin-top: 2rem;
          color: rgb(17 24 39);
        }
        
        .ProseMirror h2 {
          font-size: 1.875rem;
          font-weight: 600;
          margin-bottom: 1rem;
          margin-top: 1.5rem;
          color: rgb(17 24 39);
        }
        
        .ProseMirror h3 {
          font-size: 1.5rem;
          font-weight: 500;
          margin-bottom: 0.75rem;
          margin-top: 1.25rem;
          color: rgb(17 24 39);
        }
        
        .ProseMirror ul, .ProseMirror ol {
          padding-left: 1.5rem;
          margin-bottom: 1rem;
        }
        
        .ProseMirror li {
          margin-bottom: 0.25rem;
        }
        
        .ProseMirror blockquote {
          border-left: 4px solid rgb(249 115 22);
          padding-left: 1rem;
          font-style: italic;
          color: rgb(75 85 99);
          background-color: rgb(249 250 251);
          padding: 0.5rem 1rem;
          margin: 1rem 0;
          border-radius: 0 0.375rem 0.375rem 0;
        }
        
        .ProseMirror code {
          background-color: rgb(243 244 246);
          padding: 0.125rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.875rem;
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
          color: rgb(249 115 22);
        }
        
        .ProseMirror strong {
          font-weight: 600;
        }
        
        .ProseMirror em {
          font-style: italic;
        }
        
        /* Dark mode styles */
        .dark .ProseMirror h1,
        .dark .ProseMirror h2,
        .dark .ProseMirror h3 {
          color: rgb(243 244 246);
        }
        
        .dark .ProseMirror blockquote {
          color: rgb(209 213 219);
          background-color: rgb(31 41 55);
          border-left-color: rgb(249 115 22);
        }
        
        .dark .ProseMirror code {
          background-color: rgb(31 41 55);
          color: rgb(251 146 60);
        }
        
        .dark .ProseMirror p.is-editor-empty:first-child::before {
          color: rgb(107 114 128);
        }
      `}</style>
    </div>
  )
}

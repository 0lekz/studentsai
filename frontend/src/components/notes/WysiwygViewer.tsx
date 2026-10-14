'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Typography from '@tiptap/extension-typography'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import { useEffect } from 'react'

interface WysiwygViewerProps {
  content: string
  className?: string
  onNavigateByTitle?: (title: string) => void
}

export function WysiwygViewer({ 
  content, 
  className = "",
  onNavigateByTitle
}: WysiwygViewerProps) {
  
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable code blocks for now as they might interfere with markdown
        codeBlock: false,
      }),
      Typography,
      Link.configure({
        openOnClick: true,
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
    editable: false, // This is the key difference - read-only mode
    editorProps: {
      attributes: {
        class: `prose prose-orange max-w-none dark:prose-invert prose-lg ${className}`,
        style: `
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          line-height: 1.6;
          font-size: 16px;
          padding: 0;
        `,
      },
    },
  })

  // Update editor content when prop changes
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content, { emitUpdate: true })
    }
  }, [content, editor])

  // Handle wiki-style links if navigation function is provided
  useEffect(() => {
    if (!editor || !onNavigateByTitle) return

    const handleClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (target.tagName === 'A') {
        const href = target.getAttribute('href')
        if (href && href.startsWith('#note=')) {
          event.preventDefault()
          const title = decodeURIComponent(href.replace('#note=', ''))
          onNavigateByTitle(title)
        }
      }
    }

    const editorElement = editor.view.dom
    editorElement.addEventListener('click', handleClick)
    
    return () => {
      editorElement.removeEventListener('click', handleClick)
    }
  }, [editor, onNavigateByTitle])

  if (!editor) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
      </div>
    )
  }

  return (
    <div className="wysiwyg-viewer">
      <EditorContent 
        editor={editor} 
        className="focus:outline-none"
      />
      
      {/* Custom styles for the read-only viewer */}
      <style jsx global>{`
        .wysiwyg-viewer .ProseMirror {
          outline: none;
          cursor: default;
        }
        
        .wysiwyg-viewer .ProseMirror h1 {
          font-size: 2.25rem;
          font-weight: 700;
          margin-bottom: 1.5rem;
          margin-top: 2rem;
          color: rgb(17 24 39);
        }
        
        .wysiwyg-viewer .ProseMirror h2 {
          font-size: 1.875rem;
          font-weight: 600;
          margin-bottom: 1rem;
          margin-top: 1.5rem;
          color: rgb(17 24 39);
        }
        
        .wysiwyg-viewer .ProseMirror h3 {
          font-size: 1.5rem;
          font-weight: 500;
          margin-bottom: 0.75rem;
          margin-top: 1.25rem;
          color: rgb(17 24 39);
        }
        
        .wysiwyg-viewer .ProseMirror p {
          margin-bottom: 1rem;
          line-height: 1.6;
          color: rgb(55 65 81);
        }
        
        .wysiwyg-viewer .ProseMirror ul, 
        .wysiwyg-viewer .ProseMirror ol {
          padding-left: 1.5rem;
          margin-bottom: 1rem;
        }
        
        .wysiwyg-viewer .ProseMirror li {
          margin-bottom: 0.25rem;
          color: rgb(55 65 81);
        }
        
        .wysiwyg-viewer .ProseMirror blockquote {
          border-left: 4px solid rgb(249 115 22);
          padding-left: 1rem;
          font-style: italic;
          color: rgb(75 85 99);
          background-color: rgb(249 250 251);
          padding: 0.5rem 1rem;
          margin: 1rem 0;
          border-radius: 0 0.375rem 0.375rem 0;
        }
        
        .wysiwyg-viewer .ProseMirror code {
          background-color: rgb(243 244 246);
          padding: 0.125rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.875rem;
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
          color: rgb(249 115 22);
        }
        
        .wysiwyg-viewer .ProseMirror strong {
          font-weight: 600;
          color: rgb(17 24 39);
        }
        
        .wysiwyg-viewer .ProseMirror em {
          font-style: italic;
        }
        
        /* Dark mode styles */
        .dark .wysiwyg-viewer .ProseMirror h1,
        .dark .wysiwyg-viewer .ProseMirror h2,
        .dark .wysiwyg-viewer .ProseMirror h3 {
          color: rgb(243 244 246);
        }
        
        .dark .wysiwyg-viewer .ProseMirror p,
        .dark .wysiwyg-viewer .ProseMirror li {
          color: rgb(209 213 219);
        }
        
        .dark .wysiwyg-viewer .ProseMirror strong {
          color: rgb(243 244 246);
        }
        
        .dark .wysiwyg-viewer .ProseMirror blockquote {
          color: rgb(209 213 219);
          background-color: rgb(31 41 55);
          border-left-color: rgb(249 115 22);
        }
        
        .dark .wysiwyg-viewer .ProseMirror code {
          background-color: rgb(31 41 55);
          color: rgb(251 146 60);
        }
      `}</style>
    </div>
  )
}

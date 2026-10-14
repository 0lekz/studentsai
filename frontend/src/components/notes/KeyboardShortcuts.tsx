'use client'

import { Button } from '@/components/ui/button'
import { 
  Command, 
  X, 
  Save, 
  Bold, 
  Italic, 
  Code, 
  Link, 
  Heading1, 
  Heading2, 
  Heading3,
  List,
  ListOrdered,
  Quote,
  Focus,
  Search,
  Plus
} from 'lucide-react'

interface KeyboardShortcutsProps {
  isOpen: boolean
  onClose: () => void
}

const shortcuts = [
  {
    category: 'General',
    items: [
      { keys: ['Cmd', 'S'], description: 'Save note', icon: <Save className="h-4 w-4" /> },
      { keys: ['Cmd', 'Enter'], description: 'Enter distraction-free mode', icon: <Focus className="h-4 w-4" /> },
      { keys: ['Cmd', 'K'], description: 'Search notes', icon: <Search className="h-4 w-4" /> },
      { keys: ['Cmd', 'N'], description: 'New note', icon: <Plus className="h-4 w-4" /> },
      { keys: ['Escape'], description: 'Close modal/exit focus mode', icon: <X className="h-4 w-4" /> },
    ]
  },
  {
    category: 'Text Formatting',
    items: [
      { keys: ['Cmd', 'B'], description: 'Bold text', icon: <Bold className="h-4 w-4" /> },
      { keys: ['Cmd', 'I'], description: 'Italic text', icon: <Italic className="h-4 w-4" /> },
      { keys: ['Cmd', 'E'], description: 'Inline code', icon: <Code className="h-4 w-4" /> },
      { keys: ['Cmd', 'K'], description: 'Add link', icon: <Link className="h-4 w-4" /> },
    ]
  },
  {
    category: 'Headings',
    items: [
      { keys: ['Cmd', '1'], description: 'Heading 1', icon: <Heading1 className="h-4 w-4" /> },
      { keys: ['Cmd', '2'], description: 'Heading 2', icon: <Heading2 className="h-4 w-4" /> },
      { keys: ['Cmd', '3'], description: 'Heading 3', icon: <Heading3 className="h-4 w-4" /> },
    ]
  },
  {
    category: 'Lists & Blocks',
    items: [
      { keys: ['Cmd', 'Shift', '8'], description: 'Bullet list', icon: <List className="h-4 w-4" /> },
      { keys: ['Cmd', 'Shift', '7'], description: 'Numbered list', icon: <ListOrdered className="h-4 w-4" /> },
      { keys: ['Cmd', 'Shift', '>'], description: 'Blockquote', icon: <Quote className="h-4 w-4" /> },
    ]
  }
]

export function KeyboardShortcuts({ isOpen, onClose }: KeyboardShortcutsProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-[#141820] rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-[#232a36]">
          <div className="flex items-center space-x-3">
            <Command className="h-5 w-5 text-orange-500" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Keyboard Shortcuts</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-96">
          <div className="space-y-6">
            {shortcuts.map((category, categoryIndex) => (
              <div key={categoryIndex}>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  {category.category}
                </h3>
                <div className="space-y-2">
                  {category.items.map((shortcut, itemIndex) => (
                    <div
                      key={itemIndex}
                      className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="text-gray-500 dark:text-gray-400">
                          {shortcut.icon}
                        </div>
                        <span className="text-sm text-gray-700 dark:text-gray-300">
                          {shortcut.description}
                        </span>
                      </div>
                      <div className="flex items-center space-x-1">
                        {shortcut.keys.map((key, keyIndex) => (
                          <div key={keyIndex} className="flex items-center">
                            <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded border border-gray-200 dark:border-gray-600">
                              {key}
                            </kbd>
                            {keyIndex < shortcut.keys.length - 1 && (
                              <span className="mx-1 text-gray-400">+</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-[#232a36] bg-gray-50 dark:bg-[#0f1115]">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Press <kbd className="px-1 py-0.5 text-xs font-mono bg-gray-200 dark:bg-gray-600 rounded">?</kbd> to toggle this help
            </p>
            <Button onClick={onClose} className="bg-orange-500 hover:bg-orange-600 text-white">
              Got it
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

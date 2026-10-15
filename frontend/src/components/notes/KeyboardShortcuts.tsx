'use client'

import { useEffect, useState } from 'react'
import {
  Bold,
  Code,
  Focus,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  Link,
  List,
  ListOrdered,
  Plus,
  Quote,
  Save,
  Search,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'

interface KeyboardShortcutsProps {
  isOpen: boolean
  onClose: () => void
}

const MOD = 'Mod'

const shortcuts = [
  {
    category: 'General',
    items: [
      { keys: [MOD, 'S'], description: 'Save note in focus mode', icon: Save },
      { keys: [MOD, 'Enter'], description: 'Toggle full screen in focus mode', icon: Focus },
      { keys: [MOD, 'K'], description: 'Search notes', icon: Search },
      { keys: [MOD, 'N'], description: 'New note', icon: Plus },
      { keys: ['Esc'], description: 'Close dialog or exit focus mode', icon: X },
    ],
  },
  {
    category: 'Text formatting',
    items: [
      { keys: [MOD, 'B'], description: 'Bold', icon: Bold },
      { keys: [MOD, 'I'], description: 'Italic', icon: Italic },
      { keys: [MOD, 'E'], description: 'Inline code', icon: Code },
      { keys: [MOD, 'K'], description: 'Add link while editing', icon: Link },
    ],
  },
  {
    category: 'Headings',
    items: [
      { keys: [MOD, '1'], description: 'Heading 1', icon: Heading1 },
      { keys: [MOD, '2'], description: 'Heading 2', icon: Heading2 },
      { keys: [MOD, '3'], description: 'Heading 3', icon: Heading3 },
    ],
  },
  {
    category: 'Lists and blocks',
    items: [
      { keys: [MOD, 'Shift', '8'], description: 'Bullet list', icon: List },
      { keys: [MOD, 'Shift', '7'], description: 'Numbered list', icon: ListOrdered },
      { keys: [MOD, 'Shift', '>'], description: 'Blockquote', icon: Quote },
    ],
  },
]

function isApplePlatform(): boolean {
  const platform = (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData?.platform ?? navigator.platform
  return /mac|iphone|ipad|ipod/i.test(platform)
}

export function KeyboardShortcuts({ isOpen, onClose }: KeyboardShortcutsProps) {
  const [modLabel, setModLabel] = useState('Ctrl')

  useEffect(() => {
    setModLabel(isApplePlatform() ? 'Cmd' : 'Ctrl')
  }, [])

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85dvh] max-w-[calc(100vw-2rem)] overflow-hidden p-0 sm:max-w-xl">
        <DialogHeader className="border-b border-border px-6 py-4">
          <DialogTitle>Keyboard shortcuts</DialogTitle>
        </DialogHeader>
        <div className="max-h-[60dvh] space-y-6 overflow-y-auto px-6 py-2">
          {shortcuts.map((group) => (
            <section key={group.category}>
              <h3 className="mb-2 text-caption font-medium uppercase tracking-wide text-muted-foreground">{group.category}</h3>
              <ul className="space-y-1">
                {group.items.map(({ keys, description, icon: Icon }) => (
                  <li key={`${group.category}-${description}`} className="flex items-center justify-between gap-4 rounded-control px-2 py-1.5 hover:bg-accent">
                    <span className="flex items-center gap-3 text-body text-foreground">
                      <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
                      {description}
                    </span>
                    <span className="flex shrink-0 items-center gap-1">
                      {keys.map((key, index) => (
                        <kbd key={index} className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-caption text-muted-foreground">
                          {key === MOD ? modLabel : key}
                        </kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        <DialogFooter className="border-t border-border px-6 py-4">
          <Button onClick={onClose}>Got it</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

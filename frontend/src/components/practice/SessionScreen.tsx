'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ProgressBar } from '@/components/ui/progress-bar'

interface SessionScreenProps {
  progress?: { done: number; total: number; position: number }
  onEnd: () => void
  children: React.ReactNode
}

// Practice runs full screen, above the shell and course navigation, so nothing competes with the question.
export function SessionScreen({ progress, onEnd, children }: SessionScreenProps) {
  return (
    <DialogPrimitive.Root open onOpenChange={(open) => !open && onEnd()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Content
          aria-describedby={undefined}
          onOpenAutoFocus={(event) => event.preventDefault()}
          className="fixed inset-0 z-40 flex flex-col bg-background focus:outline-none"
        >
          <DialogPrimitive.Title className="sr-only">Practice session</DialogPrimitive.Title>
          <header className="flex h-topbar shrink-0 items-center gap-3 border-b border-border bg-surface px-2 pt-[env(safe-area-inset-top)] sm:px-gutter">
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon" aria-label="End session" className="shrink-0 text-muted-foreground">
                <X className="h-5 w-5" />
              </Button>
            </DialogPrimitive.Close>
            <div className="mx-auto flex w-full max-w-prose items-center gap-3">
              <ProgressBar value={progress ? progress.done / progress.total : undefined} label="Session progress" className="flex-1" />
              {progress && (
                <span className="w-12 shrink-0 text-right text-caption font-medium tabular-nums text-muted-foreground">
                  {progress.position} / {progress.total}
                </span>
              )}
            </div>
            <span aria-hidden className="hidden w-10 shrink-0 sm:block" />
          </header>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

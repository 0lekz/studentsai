'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'

interface SheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: React.ReactNode
  description?: React.ReactNode
  children: React.ReactNode
}

// A bottom sheet on phones and a right-hand panel from the md breakpoint up.
export function Sheet({ open, onOpenChange, title, description, children }: SheetProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content
          {...(description ? {} : { 'aria-describedby': undefined })}
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-[85dvh] flex-col rounded-t-card border-t border-border bg-surface pb-[env(safe-area-inset-bottom)] shadow-xl duration-200 focus:outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom md:inset-y-0 md:left-auto md:right-0 md:h-full md:max-h-none md:w-[28rem] md:rounded-none md:border-l md:border-t-0 md:data-[state=closed]:slide-out-to-bottom-0 md:data-[state=closed]:slide-out-to-right md:data-[state=open]:slide-in-from-bottom-0 md:data-[state=open]:slide-in-from-right"
        >
          <div aria-hidden className="mx-auto mt-2 h-1 w-10 shrink-0 rounded-full bg-border md:hidden" />
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-5 pb-4 pt-3 md:pt-5">
            <div className="min-w-0">
              <DialogPrimitive.Title className="text-title font-semibold text-foreground">{title}</DialogPrimitive.Title>
              {description && <DialogPrimitive.Description className="mt-0.5 text-body text-muted-foreground">{description}</DialogPrimitive.Description>}
            </div>
            <DialogPrimitive.Close
              aria-label="Close"
              className="-mr-2 flex h-10 w-10 shrink-0 items-center justify-center rounded-control text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <X className="h-5 w-5" />
            </DialogPrimitive.Close>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

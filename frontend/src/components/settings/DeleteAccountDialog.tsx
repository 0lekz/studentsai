'use client'

import { useState } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

const CONFIRMATION_WORD = 'DELETE'

interface DeleteAccountDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => Promise<void>
}

export function DeleteAccountDialog({ open, onOpenChange, onConfirm }: DeleteAccountDialogProps) {
  const [confirmation, setConfirmation] = useState('')
  const [deleting, setDeleting] = useState(false)

  const close = (next: boolean) => {
    if (!next) setConfirmation('')
    onOpenChange(next)
  }

  const confirm = async () => {
    setDeleting(true)
    try {
      await onConfirm()
      close(false)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" aria-hidden />
            <DialogTitle>Delete account</DialogTitle>
          </div>
          <DialogDescription>
            This removes your courses, materials, notes and flashcards and cannot be undone. We email you a link to confirm. Type <strong>{CONFIRMATION_WORD}</strong> to continue.
          </DialogDescription>
        </DialogHeader>
        <Input
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
          placeholder={`Type ${CONFIRMATION_WORD} to confirm`}
          aria-label="Confirmation"
        />
        <DialogFooter className="gap-2 sm:space-x-0">
          <Button variant="outline" onClick={() => close(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={confirm} disabled={confirmation !== CONFIRMATION_WORD || deleting}>
            {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
            {deleting ? 'Sending email...' : 'Delete account'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

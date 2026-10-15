'use client'

import { useState } from 'react'
import { LogOut, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { DeleteAccountDialog } from './DeleteAccountDialog'

export function AccountSettings({ onSignOut }: { onSignOut: () => void }) {
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const requestDeletion = async () => {
    try {
      await api.requestAccountDeletion()
      setMessage({ type: 'success', text: 'Check your inbox and click the link to confirm deleting your account.' })
    } catch (error) {
      console.error('Account deletion request failed:', error)
      setMessage({
        type: 'error',
        text: (error instanceof Error && error.message) || 'Failed to send the deletion email. Please try again or contact support.',
      })
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-card border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-body font-medium text-foreground">Sign out</p>
          <p className="text-caption text-muted-foreground">Sign out of StudentsAI on this device.</p>
        </div>
        <Button variant="outline" onClick={onSignOut}>
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
      <div className="flex flex-col gap-3 rounded-card border border-destructive/40 bg-surface p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-body font-medium text-destructive">Delete account</p>
          <p className="text-caption text-muted-foreground">Permanently delete your account and everything in it.</p>
        </div>
        <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
          <Trash2 className="h-4 w-4" />
          Delete account
        </Button>
      </div>
      {message && <Alert variant={message.type === 'success' ? 'success' : 'error'}>{message.text}</Alert>}
      <DeleteAccountDialog open={deleteOpen} onOpenChange={setDeleteOpen} onConfirm={requestDeletion} />
    </div>
  )
}

'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { CheckCircle, Loader2, XCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type Status = 'loading' | 'success' | 'error'

export default function VerifyEmailChangePage() {
  const { token } = useParams<{ token: string }>()
  const [status, setStatus] = useState<Status>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Invalid verification link')
      return
    }

    api.verifyEmailChange(token)
      .then((result) => {
        if (!result.verified) {
          setStatus('error')
          setMessage(result.message || 'Email change verification failed')
          return
        }
        if (result.access_token) {
          api.setToken(result.access_token)
          localStorage.removeItem('user')
        }
        setStatus('success')
        setMessage(result.message)
      })
      .catch((error) => {
        setStatus('error')
        setMessage(error instanceof Error ? error.message : 'Failed to verify the email change.')
      })
  }, [token])

  const Icon = status === 'loading' ? Loader2 : status === 'success' ? CheckCircle : XCircle

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-gutter">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <Icon
            aria-hidden
            className={
              status === 'loading'
                ? 'mx-auto mb-2 h-10 w-10 animate-spin text-muted-foreground'
                : status === 'success'
                  ? 'mx-auto mb-2 h-10 w-10 text-success'
                  : 'mx-auto mb-2 h-10 w-10 text-destructive'
            }
          />
          <CardTitle className="text-title">
            {status === 'loading' ? 'Confirming your new email' : status === 'success' ? 'Email changed' : 'Email change failed'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-body text-muted-foreground">
            {status === 'loading' ? 'One moment while we confirm the link.' : message}
          </p>
          {status !== 'loading' && (
            <Button asChild className="w-full">
              <Link href={api.hasToken() ? '/settings' : '/auth'}>{api.hasToken() ? 'Go to settings' : 'Sign in'}</Link>
            </Button>
          )}
        </CardContent>
      </Card>
    </main>
  )
}

'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

function GoogleCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    const handleGoogleCallback = async () => {
      const token = searchParams.get('token')
      const userId = searchParams.get('user_id')
      const email = searchParams.get('email')
      const username = searchParams.get('username')
      const verified = searchParams.get('verified')
      const error = searchParams.get('error')
      const message = searchParams.get('message')
      const code = searchParams.get('code')

      if (error) {
        setStatus('error')
        setError(message || 'Google authentication was cancelled or failed')
        return
      }

      try {
        if (token && userId) {
          api.setToken(token)
          if (typeof window !== 'undefined') {
            localStorage.setItem('user', JSON.stringify({
              id: userId,
              email: email || '',
              username: username || '',
              verified: verified === 'true',
              created_at: new Date().toISOString(),
            }))
          }
          setStatus('success')
          setTimeout(() => router.replace('/'), 1000)
          return
        }

        // Fallback: if we only have a code, exchange it via API
        if (code) {
          const resp = await api.googleAuth(code)
          if (resp?.access_token && resp?.user) {
            api.setToken(resp.access_token)
            if (typeof window !== 'undefined') {
              localStorage.setItem('user', JSON.stringify(resp.user))
            }
            setStatus('success')
            setTimeout(() => router.replace('/'), 1000)
            return
          }
        }

        setStatus('error')
        setError('No authentication token received from Google')
      } catch (err) {
        setStatus('error')
        setError((err instanceof Error && err.message) || 'Failed to complete Google authentication')
        console.error('Google auth error:', err)
      }
    }

    handleGoogleCallback()
  }, [searchParams, router])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardContent className="text-center py-8">
            <Loader2 className="w-12 h-12 text-orange-500 animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Completing Google Sign-In
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Please wait while we complete your authentication...
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardContent className="text-center py-8">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Welcome to StudentsAI!
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Your Google account has been successfully connected. Redirecting you to the dashboard...
            </p>
            <Button onClick={() => router.replace('/')} className="bg-orange-600 hover:bg-orange-700">
              Go to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardContent className="text-center py-8">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Authentication Failed
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {error}
          </p>
          <div className="space-y-2">
            <Button onClick={() => router.replace('/auth')} className="w-full bg-orange-600 hover:bg-orange-700">
              Try Again
            </Button>
            <Button 
              onClick={() => router.replace('/')} 
              variant="outline" 
              className="w-full"
            >
              Go Home
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardContent className="text-center py-8">
            <Loader2 className="w-12 h-12 text-orange-500 animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Loading…</h2>
          </CardContent>
        </Card>
      </div>
    }>
      <GoogleCallbackContent />
    </Suspense>
  )
}

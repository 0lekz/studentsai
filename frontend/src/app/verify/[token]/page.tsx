"use client"

import { useParams, useRouter, useSearchParams } from "next/navigation"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle, XCircle, Loader2 } from "lucide-react"

interface VerificationResponse {
  message: string
  verified: boolean
}

export default function VerifyEmailPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = params.token as string
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [countdown, setCountdown] = useState(3)

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Invalid verification link')
      return
    }

    const type = searchParams.get('type')
    if (type === 'account_delete') {
      fetch(`${process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || ''}/auth/confirm-account-deletion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      })
        .then(response => {
          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
          return response.json()
        })
        .then((data: { message: string }) => {
          setStatus('success')
          setMessage(data.message || 'Account deleted successfully.')
          setTimeout(() => router.replace('/landing'), 2000)
        })
        .catch(error => {
          console.error('Account deletion error:', error)
          setStatus('error')
          setMessage('Failed to delete account. The link may be invalid or expired.')
        })
      return
    }

    // Email verification flow
    fetch(`${process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || ''}/auth/verify/${token}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        return response.json()
      })
      .then((data: VerificationResponse) => {
        if (data.verified) {
          setStatus('success')
          setMessage(data.message)
          // Start countdown to redirect
          const timer = setInterval(() => {
            setCountdown(prev => {
              if (prev <= 1) {
                clearInterval(timer)
                router.push('/auth')
              }
              return prev - 1
            })
          }, 1000)
        } else {
          setStatus('error')
          setMessage(data.message || 'Verification failed')
        }
      })
      .catch(error => {
        console.error('Verification error:', error)
        setStatus('error')
        setMessage('Failed to verify email. Please try again or contact support.')
      })
  }, [token, router, searchParams])

  const handleResendVerification = () => {
    // TODO: Implement resend verification
    alert('Resend verification feature coming soon!')
  }

  const handleGoToLogin = () => {
    router.push('/auth')
  }

  if (status === 'loading') {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4">
              <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
            </div>
            <CardTitle className="text-xl">Verifying Your Email</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-gray-600 dark:text-gray-400">
              Please wait while we verify your email address...
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            {status === 'success' ? (
              <CheckCircle className="h-12 w-12 text-green-600" />
            ) : (
              <XCircle className="h-12 w-12 text-red-600" />
            )}
          </div>
          <CardTitle className="text-xl">
            {status === 'success' ? 'Success' : 'Verification Failed'}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            {message}
          </p>
          
          {status === 'success' && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
              <p className="text-sm text-green-800 dark:text-green-200">
                Redirecting to login in {countdown} seconds...
              </p>
            </div>
          )}
          
          {status === 'error' && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <p className="text-sm text-red-800 dark:text-red-200">
                Please check your email for a valid verification link or try registering again.
              </p>
            </div>
          )}
          
          <div className="flex flex-col space-y-2 pt-4">
            {status === 'success' ? (
              <Button onClick={handleGoToLogin} className="w-full">
                Go to Login Now
              </Button>
            ) : (
              <>
                <Button onClick={handleResendVerification} variant="outline" className="w-full">
                  Resend Verification Email
                </Button>
                <Button onClick={handleGoToLogin} className="w-full">
                  Back to Login
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

"use client"

import { useParams, useRouter } from "next/navigation"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle, XCircle, Loader2 } from "lucide-react"

interface VerificationResponse {
  message: string
  verified: boolean
}

export default function VerifyEmailChangePage() {
  const params = useParams()
  const router = useRouter()
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

    // Call the email change verification endpoint
    fetch(`${process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || ''}/auth/verify-email-change`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
      },
      body: JSON.stringify({ token }),
    })
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
                router.push('/settings')
              }
              return prev - 1
            })
          }, 1000)
        } else {
          setStatus('error')
          setMessage(data.message || 'Email change verification failed')
        }
      })
      .catch(error => {
        console.error('Verification error:', error)
        setStatus('error')
        setMessage('Failed to verify email change. Please try again or contact support.')
      })
  }, [token, router])

  const handleGoToSettings = () => {
    router.push('/settings')
  }

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4">
              <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
            </div>
            <CardTitle className="text-xl text-gray-900 dark:text-gray-100">
              Verifying Email Change
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-gray-600 dark:text-gray-400">
              Please wait while we verify your new email address...
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <Card className="w-full max-w-md bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            {status === 'success' ? (
              <CheckCircle className="h-12 w-12 text-green-600" />
            ) : (
              <XCircle className="h-12 w-12 text-red-600" />
            )}
          </div>
          <CardTitle className="text-xl text-gray-900 dark:text-gray-100">
            {status === 'success' ? 'Email Changed Successfully!' : 'Email Change Failed'}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            {message}
          </p>
          
          {status === 'success' && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
              <p className="text-sm text-green-800 dark:text-green-200">
                Redirecting to settings in {countdown} seconds...
              </p>
            </div>
          )}
          
          {status === 'error' && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <p className="text-sm text-red-800 dark:text-red-200">
                Please check your email for a valid verification link or try again.
              </p>
            </div>
          )}
          
          <div className="flex flex-col space-y-2 pt-4">
            <Button onClick={handleGoToSettings} className="w-full">
              {status === 'success' ? 'Go to Settings Now' : 'Back to Settings'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

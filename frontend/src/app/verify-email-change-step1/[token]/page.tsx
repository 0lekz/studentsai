"use client"

import { useParams, useRouter, useSearchParams } from "next/navigation"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { XCircle, Loader2, Shield } from "lucide-react"

interface VerificationResponse {
  message: string
  verified: boolean
}

export default function VerifyEmailChangeStep1Page() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = params.token as string
  const newEmail = searchParams.get('new_email')
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let isMounted = true

    if (!token || !newEmail) {
      if (isMounted) {
        setStatus('error')
        setMessage('Invalid verification link')
      }
      return
    }

    // Call the step 1 verification endpoint
    fetch(`${process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || ''}/auth/verify-email-change-step1/${token}?new_email=${encodeURIComponent(newEmail)}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        return response.json()
      })
      .then((data: VerificationResponse) => {
        if (!isMounted) return
        
        if (data.verified) {
          setStatus('success')
          setMessage(data.message)
          // Use setTimeout instead of setInterval to avoid React state conflicts
          setTimeout(() => {
            if (isMounted) {
              router.push('/settings')
            }
          }, 3000)
        } else {
          setStatus('error')
          setMessage(data.message || 'Account ownership verification failed')
        }
      })
      .catch(error => {
        if (!isMounted) return
        
        console.error('Verification error:', error)
        setStatus('error')
        setMessage('Failed to verify account ownership. Please try again or contact support.')
      })

    // Cleanup function
    return () => {
      isMounted = false
    }
  }, [token, newEmail, router])

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
              Verifying Account Ownership
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-gray-600 dark:text-gray-400">
              Please wait while we verify you own this account...
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
              <Shield className="h-12 w-12 text-green-600" />
            ) : (
              <XCircle className="h-12 w-12 text-red-600" />
            )}
          </div>
          <CardTitle className="text-xl text-gray-900 dark:text-gray-100">
            {status === 'success' ? 'Account Ownership Verified!' : 'Verification Failed'}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            {message}
          </p>
          
          {status === 'success' && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
              <p className="text-sm text-green-800 dark:text-green-200">
                Verification email sent to: <strong>{newEmail}</strong>
              </p>
              <p className="text-sm text-green-800 dark:text-green-200 mt-1">
                Redirecting to settings in 3 seconds...
              </p>
            </div>
          )}
          
          {status === 'error' && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <p className="text-sm text-red-800 dark:text-red-200">
                Please check your current email for a valid verification link or try again.
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

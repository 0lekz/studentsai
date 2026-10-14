'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api, APIError } from '@/lib/api'
import { Mail, User, Lock, AlertCircle, CheckCircle } from 'lucide-react'

interface AuthFormProps {
  onSuccess: () => void
}

export function AuthForm({ onSuccess }: AuthFormProps) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      if (isLogin) {
        const response = await api.login(email, password)
        // API client already stores the token, just store user data
        if (typeof window !== 'undefined' && response.user) {
          localStorage.setItem('user', JSON.stringify(response.user))
        }
        onSuccess()
      } else {
        const response = await api.register(email, password, username)
        // API client already stores the token, just store user data
        if (typeof window !== 'undefined' && response.user) {
          localStorage.setItem('user', JSON.stringify(response.user))
        }
        setSuccess('Registration successful! Please check your email to verify your account before logging in.')
        // Clear form after successful registration
        setEmail('')
        setUsername('')
        setPassword('')
        // Switch to login mode
        setIsLogin(true)
      }
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message)
        // Handle specific verification errors
        if (err.message.includes('not verified') || err.message.includes('verify')) {
          setError('Please verify your email address before logging in. Check your inbox for the verification link.')
        }
      } else {
        setError('An unexpected error occurred')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleAuth = async () => {
    setGoogleLoading(true)
    setError('')
    
    try {
      // Redirect to Google OAuth
      window.location.href = `${process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || ''}/auth/google/login`
    } catch {
      setError('Failed to initiate Google sign-in')
    } finally {
      setGoogleLoading(false)
    }
  }

  const clearMessages = () => {
    setError('')
    setSuccess('')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            StudentsAI
          </CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            {isLogin ? 'Sign in to your account' : 'Create a new account'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Google OAuth Button */}
          <Button
            type="button"
            onClick={handleGoogleAuth}
            disabled={googleLoading}
            className="w-full mb-6 bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 hover:border-gray-400 flex items-center justify-center space-x-2"
          >
            {googleLoading ? (
              <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
            )}
            <span>{googleLoading ? 'Signing in...' : 'Continue with Google'}</span>
          </Button>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white dark:bg-[#141820] text-gray-500 dark:text-gray-400">
                {isLogin ? 'Or sign in with email' : 'Or sign up with email'}
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-md flex items-start space-x-2">
                <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}
            
            {success && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-3 rounded-md flex items-start space-x-2">
                <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{success}</span>
              </div>
            )}
            
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    clearMessages()
                  }}
                  required
                  placeholder="Enter your email"
                  className="pl-10 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 border-gray-200 dark:border-[#232a36] focus:border-orange-500 dark:focus:border-orange-400"
                />
              </div>
            </div>

            {!isLogin && (
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value)
                      clearMessages()
                    }}
                    required
                    placeholder="Choose a username"
                    minLength={3}
                    maxLength={50}
                    className="pl-10 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 border-gray-200 dark:border-[#232a36] focus:border-orange-500 dark:focus:border-orange-400"
                  />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Letters, numbers, underscores, and hyphens only
                </p>
              </div>
            )}

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    clearMessages()
                  }}
                  required
                  placeholder="Enter your password"
                  minLength={8}
                  className="pl-10 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 border-gray-200 dark:border-[#232a36] focus:border-orange-500 dark:focus:border-orange-400"
                />
              </div>
              {!isLogin && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Must be at least 8 characters long
                </p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full bg-orange-600 hover:bg-orange-700 text-white"
              disabled={loading}
            >
              {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Sign Up')}
            </Button>

            <div className="text-center">
              <button
                type="button"
                onClick={() => {
                  setIsLogin(!isLogin)
                  clearMessages()
                }}
                className="text-sm text-orange-500 hover:text-orange-600 underline"
              >
                {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
              </button>
            </div>

            {!isLogin && (
              <div className="text-center">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  By signing up, you agree to our terms and will receive a verification email.
                </p>
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  )
}


/**
 * ProfileSettings: User profile management with enhanced security and privacy
 */
'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/form-label'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, XCircle, Loader2, Eye, EyeOff, AlertTriangle, Shield, Lock, User as UserIcon } from 'lucide-react'
import { api, type User, type UserProfileUpdate } from '@/lib/api'

interface ProfileSettingsProps {
  user: User
  onUserUpdate: (user: User) => void
}

export function ProfileSettings({ user, onUserUpdate }: ProfileSettingsProps) {
  const [formData, setFormData] = useState({
    username: user.username,
    email: user.email,
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })
  
  const [usernameStatus, setUsernameStatus] = useState<{
    checking: boolean
    available: boolean | null
    message: string
  }>({ checking: false, available: null, message: '' })
  
  const [passwordVisible, setPasswordVisible] = useState({
    current: false,
    new: false,
    confirm: false,
  })
  
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null)
  
  // Security states
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [attemptCount, setAttemptCount] = useState(0)
  const [lastAttemptTime, setLastAttemptTime] = useState(0)

  // Password strength validation
  const [passwordStrength, setPasswordStrength] = useState({
    score: 0,
    feedback: '',
    meetsRequirements: false
  })

  // Check username availability when username changes
  useEffect(() => {
    const checkUsername = async () => {
      if (!formData.username || formData.username === user.username) {
        setUsernameStatus({ checking: false, available: null, message: '' })
        return
      }

      if (formData.username.length < 3) {
        setUsernameStatus({ checking: false, available: false, message: 'Username must be at least 3 characters' })
        return
      }

      // Username validation rules
      const usernameRegex = /^[a-zA-Z0-9_-]+$/
      if (!usernameRegex.test(formData.username)) {
        setUsernameStatus({ checking: false, available: false, message: 'Username can only contain letters, numbers, underscores, and hyphens' })
        return
      }

      setUsernameStatus({ checking: true, available: null, message: 'Checking availability...' })
      
      try {
        const result = await api.checkUsernameAvailability(formData.username)
        setUsernameStatus({
          checking: false,
          available: result.available,
          message: result.available ? 'Username available!' : 'Username already taken'
        })
      } catch {
        setUsernameStatus({
          checking: false,
          available: false,
          message: 'Error checking username'
        })
      }
    }

    const timeoutId = setTimeout(checkUsername, 500)
    return () => clearTimeout(timeoutId)
  }, [formData.username, user.username])

  // Password strength checker
  useEffect(() => {
    if (!formData.newPassword) {
      setPasswordStrength({ score: 0, feedback: '', meetsRequirements: false })
      return
    }

    let score = 0
    const feedback = []

    // Length check
    if (formData.newPassword.length >= 8) score += 1
    else feedback.push('At least 8 characters')

    // Complexity checks
    if (/[a-z]/.test(formData.newPassword)) score += 1
    else feedback.push('Include lowercase letters')

    if (/[A-Z]/.test(formData.newPassword)) score += 1
    else feedback.push('Include uppercase letters')

    if (/[0-9]/.test(formData.newPassword)) score += 1
    else feedback.push('Include numbers')

    if (/[^A-Za-z0-9]/.test(formData.newPassword)) score += 1
    else feedback.push('Include special characters')

    // Common password check (basic)
    const commonPasswords = ['password', '123456', 'qwerty', 'admin', 'letmein']
    if (!commonPasswords.includes(formData.newPassword.toLowerCase())) score += 1
    else feedback.push('Avoid common passwords')

    setPasswordStrength({
      score,
      feedback: feedback.join(', '),
      meetsRequirements: score >= 4 && formData.newPassword.length >= 8
    })
  }, [formData.newPassword])

  // Rate limiting
  const checkRateLimit = () => {
    const now = Date.now()
    const timeWindow = 15 * 60 * 1000 // 15 minutes
    
    if (now - lastAttemptTime < timeWindow && attemptCount >= 5) {
      const remainingTime = Math.ceil((timeWindow - (now - lastAttemptTime)) / 1000 / 60)
      throw new Error(`Too many attempts. Please wait ${remainingTime} minutes before trying again.`)
    }
    
    if (now - lastAttemptTime > timeWindow) {
      setAttemptCount(0)
    }
    
    setAttemptCount(prev => prev + 1)
    setLastAttemptTime(now)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      checkRateLimit()
    } catch (error) {
      setMessage({ type: 'error', text: error instanceof Error ? error.message : String(error) })
      return
    }

    setIsLoading(true)
    setMessage(null)

    try {
      // Enhanced validation
      if (formData.newPassword) {
        if (!passwordStrength.meetsRequirements) {
          setMessage({ type: 'error', text: 'Password does not meet security requirements' })
          setIsLoading(false)
          return
        }
        
        if (formData.newPassword !== formData.confirmPassword) {
          setMessage({ type: 'error', text: 'New passwords do not match' })
          setIsLoading(false)
          return
        }
        
        if (formData.newPassword === formData.currentPassword) {
          setMessage({ type: 'error', text: 'New password must be different from current password' })
          setIsLoading(false)
          return
        }

        // Require current password for password changes only if user already has a password
        if (!isSetPassword && !formData.currentPassword) {
          setMessage({ type: 'error', text: 'Current password is required to change password' })
          setIsLoading(false)
          return
        }
      }

      // Require current password for email changes
      if (formData.email !== user.email && !formData.currentPassword && !isSetPassword) {
        setMessage({ type: 'error', text: 'Current password is required to change email address' })
        setIsLoading(false)
        return
      }

      // Handle email change verification
      if (formData.email !== user.email) {
        try {
          // Send verification email to new email address
          await api.sendEmailChangeVerification(formData.email)

          setMessage({ 
            type: 'success', 
            text: `Verification email sent to your current email address (${user.email}). Please check your inbox and click the verification link to confirm you own this account. After verification, you'll receive another email at ${formData.email} to complete the change.` 
          })
          
          // Reset form but keep the new email for reference
          setFormData(prev => ({
            ...prev,
            currentPassword: '',
            newPassword: '',
            confirmPassword: '',
          }))
          
          setIsLoading(false)
          return
        } catch {
          setMessage({ 
            type: 'error', 
            text: 'Failed to send verification email. Please try again.' 
          })
          setIsLoading(false)
          return
        }
      }

      // Prepare update data (excluding email since it requires verification)
      const updateData: UserProfileUpdate = {}
      if (formData.username !== user.username) updateData.username = formData.username
      if (formData.newPassword) {
        if (!isSetPassword) {
          updateData.current_password = formData.currentPassword
        }
        updateData.new_password = formData.newPassword
      }

      if (Object.keys(updateData).length === 0) {
        setMessage({ type: 'warning', text: 'No changes to save' })
        setIsLoading(false)
        return
      }

      // Show confirmation for sensitive changes
      let requiresConfirmation = false
      let confirmationMessage = ''

      if (formData.newPassword) {
        requiresConfirmation = true
        confirmationMessage = 'Are you sure you want to change your password? You will be logged out of all other devices.'
      }

      if (requiresConfirmation) {
        if (!confirm(confirmationMessage)) {
          setIsLoading(false)
          return
        }
      }

      // Update profile (username and password only)
      const updatedUser = await api.updateProfileSettings(updateData)
      onUserUpdate(updatedUser)
      
      // Reset form
      setFormData(prev => ({
        ...prev,
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      }))
      
      let successMessage = 'Profile updated successfully!'
      if (formData.newPassword) {
        successMessage += ' Your password has been changed. For security, you have been logged out of all other devices.'
        // Here you would typically redirect to login or refresh the session
      }
      
      setMessage({ type: 'success', text: successMessage })
      
      // Reset attempt count on success
      setAttemptCount(0)
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: (error instanceof Error && error.message) || 'Failed to update profile. Please try again later.'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const togglePasswordVisibility = (field: 'current' | 'new' | 'confirm') => {
    setPasswordVisible(prev => ({
      ...prev,
      [field]: !prev[field]
    }))
  }

  const getPasswordStrengthColor = (score: number) => {
    if (score <= 2) return 'text-red-500'
    if (score <= 3) return 'text-orange-500'
    if (score <= 4) return 'text-yellow-500'
    return 'text-green-500'
  }

  const getPasswordStrengthText = (score: number) => {
    if (score <= 2) return 'Weak'
    if (score <= 3) return 'Fair'
    if (score <= 4) return 'Good'
    return 'Strong'
  }

  const isSetPassword = user.has_password === false

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Profile Settings</h2>
        <p className="text-gray-600 dark:text-gray-400">
          Manage your account information and security settings
        </p>
      </div>

      {/* Security Notice */}
      <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <CardContent className="pt-6">
          <div className="flex items-start space-x-3">
            <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-blue-800 dark:text-blue-200">
              <p className="font-medium">Security Notice</p>
              <p className="mt-1">
                All changes to your profile require verification. Email changes will require confirmation, 
                and password changes require your current password for security.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Username Section */}
        <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
              <UserIcon className="h-5 w-5" />
              <span>Username</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="username" className="text-gray-700 dark:text-gray-300">Username</Label>
              <div className="relative">
                <Input
                  id="username"
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                  className="pr-20 border-gray-300 dark:border-gray-600 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20"
                  placeholder="Enter username"
                  maxLength={30}
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  {usernameStatus.checking && <Loader2 className="h-4 w-4 animate-spin text-gray-400" />}
                  {!usernameStatus.checking && usernameStatus.available === true && (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  )}
                  {!usernameStatus.checking && usernameStatus.available === false && (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                </div>
              </div>
              {usernameStatus.message && (
                <div className="mt-2">
                  <Badge 
                    variant={usernameStatus.available ? 'default' : 'destructive'}
                    className="text-xs"
                  >
                    {usernameStatus.message}
                  </Badge>
                </div>
              )}
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Username can only contain letters, numbers, underscores, and hyphens. 3-30 characters.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Email Section */}
        <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
              <UserIcon className="h-5 w-5" />
              <span>Email Address</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div>
              <Label htmlFor="email" className="text-gray-700 dark:text-gray-300">
                Email
                {formData.email !== user.email && (
                  <span className="text-red-500 ml-1">*</span>
                )}
              </Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                className="border-gray-300 dark:border-gray-600 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20"
                placeholder="Enter email address"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {formData.email !== user.email 
                  ? 'Email changes require current password verification. You\'ll receive a confirmation email.'
                  : 'Email changes require verification. You\'ll receive a confirmation email.'
                }
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Password Section */}
        <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
              <Lock className="h-5 w-5" />
              <span>{isSetPassword ? 'Set Password' : 'Change Password'}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="currentPassword" className="text-gray-700 dark:text-gray-300">
                {isSetPassword ? 'Current Password (not required for Google sign-in users)' : 'Current Password'}
                {!isSetPassword && <span className="text-red-500 ml-1">*</span>}
              </Label>
              <div className="relative">
                <Input
                  id="currentPassword"
                  type={passwordVisible.current ? 'text' : 'password'}
                  value={formData.currentPassword}
                  onChange={(e) => setFormData(prev => ({ ...prev, currentPassword: e.target.value }))}
                  className="pr-20 border-gray-300 dark:border-gray-600 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20"
                  placeholder="Enter current password"
                  required={!isSetPassword}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => togglePasswordVisibility('current')}
                >
                  {passwordVisible.current ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {isSetPassword ? 'You can set a password without current password.' : 'Required for password changes and email changes'}
              </p>
            </div>

            <div>
              <Label htmlFor="newPassword" className="text-gray-700 dark:text-gray-300">New Password</Label>
              <div className="relative">
                <Input
                  id="newPassword"
                  type={passwordVisible.new ? 'text' : 'password'}
                  value={formData.newPassword}
                  onChange={(e) => setFormData(prev => ({ ...prev, newPassword: e.target.value }))}
                  className="pr-20 border-gray-300 dark:border-gray-600 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20"
                  placeholder="Enter new password"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => togglePasswordVisibility('new')}
                >
                  {passwordVisible.new ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              
              {/* Password strength indicator */}
              {formData.newPassword && (
                <div className="mt-2 space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-600 dark:text-gray-400">Strength:</span>
                    <span className={`text-xs font-medium ${getPasswordStrengthColor(passwordStrength.score)}`}>
                      {getPasswordStrengthText(passwordStrength.score)}
                    </span>
                    <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-300 ${
                          passwordStrength.score <= 2 ? 'bg-red-500' :
                          passwordStrength.score <= 3 ? 'bg-orange-500' :
                          passwordStrength.score <= 4 ? 'bg-yellow-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${(passwordStrength.score / 6) * 100}%` }}
                      />
                    </div>
                  </div>
                  {passwordStrength.feedback && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {passwordStrength.feedback}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div>
              <Label htmlFor="confirmPassword" className="text-gray-700 dark:text-gray-300">Confirm New Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={passwordVisible.confirm ? 'text' : 'password'}
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  className="pr-20 border-gray-300 dark:border-gray-600 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20"
                  placeholder="Confirm new password"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => togglePasswordVisibility('confirm')}
                >
                  {passwordVisible.confirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* Security notice for password changes */}
            {(formData.newPassword || formData.email !== user.email) && (
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-yellow-700 dark:text-yellow-300">
                    <p className="font-medium">Security Notice</p>
                    <p className="mt-1">
                      {formData.newPassword && 'Password changes will log you out of all other devices. '}
                      {formData.email !== user.email && 'Email changes require verification before accessing certain features.'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Message Display */}
        {message && (
          <div className={`p-4 rounded-lg ${
            message.type === 'success' 
              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-200' 
              : message.type === 'warning'
              ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200'
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200'
          }`}>
            {message.text}
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end">
          <Button 
            type="submit" 
            disabled={isLoading || (!!formData.newPassword && !passwordStrength.meetsRequirements)}
            className="bg-orange-600 hover:bg-orange-700 dark:bg-orange-600 dark:hover:bg-orange-700 text-white border-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </Button>
        </div>
      </form>

      {/* Account Deletion Section */}
      <Card className="border-red-200 dark:border-red-800 bg-white dark:bg-[#141820]">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-red-600 dark:text-red-400">
            <AlertTriangle className="h-5 w-5" />
            <span>Danger Zone</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-base text-red-600 dark:text-red-400">Delete Account</span>
                <p className="text-sm text-red-500 dark:text-red-400 mt-1">
                  Permanently delete your account and all associated data
                </p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeleteConfirm(true)}
                className="bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 text-white border-0 shadow-sm"
              >
                <AlertTriangle className="h-4 w-4 mr-2" />
                Delete Account
              </Button>
            </div>
            
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-start space-x-2">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-red-700 dark:text-red-300">
                  <p className="font-medium">Warning</p>
                  <p className="mt-1">This action cannot be undone. All your notes, flashcards, progress, and account data will be permanently deleted.</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#141820] p-6 rounded-lg max-w-md w-full mx-4 border border-red-200 dark:border-red-800">
            <div className="flex items-center space-x-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Confirm Account Deletion</h3>
            </div>
            
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                This action is irreversible. To confirm deletion, please type <strong>DELETE</strong> below.
              </p>
              
              <Input
                type="text"
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                placeholder="Type DELETE to confirm"
                className="border-gray-300 dark:border-gray-600 bg-white dark:bg-[#1d2430] text-gray-900 dark:text-gray-100"
              />
              
              <div className="flex space-x-3">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowDeleteConfirm(false)
                    setDeleteConfirmation('')
                  }}
                  className="flex-1 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 bg-white dark:bg-[#1d2430]"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  disabled={deleteConfirmation !== 'DELETE' || isDeleting}
                  onClick={async () => {
                    setIsDeleting(true)
                    try {
                      await api.requestAccountDeletion()
                      setMessage({ 
                        type: 'success', 
                        text: 'Account deletion email sent! Please check your inbox and click the confirmation link.' 
                      })
                      setShowDeleteConfirm(false)
                      setDeleteConfirmation('')
                    } catch (e) {
                      console.error('Account deletion request failed:', e)
                      setMessage({ 
                        type: 'error', 
                        text: (e instanceof Error && e.message) || 'Failed to send deletion email. Please try again or contact support.'
                      })
                    } finally {
                      setIsDeleting(false)
                    }
                  }}
                  className="flex-1 bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 text-white border-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isDeleting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Sending Email...
                    </>
                  ) : (
                    'Delete Account'
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

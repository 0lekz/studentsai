'use client'

import { useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { api, type User, type UserProfileUpdate } from '@/lib/api'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/form-label'
import { PasswordField } from './PasswordField'
import { PasswordStrengthMeter } from './PasswordStrengthMeter'
import { UsernameField } from './UsernameField'
import { evaluatePasswordStrength } from './passwordStrength'
import { useUsernameAvailability } from './useUsernameAvailability'

const ATTEMPT_WINDOW_MS = 15 * 60 * 1000
const MAX_ATTEMPTS = 5

type FormMessage = { type: 'success' | 'error' | 'warning'; text: string }

interface ProfileSettingsProps {
  user: User
  onUserUpdate: (user: User) => void
}

const EMPTY_PASSWORDS = { currentPassword: '', newPassword: '', confirmPassword: '' }

export function ProfileSettings({ user, onUserUpdate }: ProfileSettingsProps) {
  const [username, setUsername] = useState(user.username)
  const [email, setEmail] = useState(user.email)
  const [passwords, setPasswords] = useState(EMPTY_PASSWORDS)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<FormMessage | null>(null)
  const [attempts, setAttempts] = useState({ count: 0, lastAt: 0 })

  const usernameStatus = useUsernameAvailability(username, user.username)
  const passwordStrength = useMemo(() => evaluatePasswordStrength(passwords.newPassword), [passwords.newPassword])
  const isSetPassword = user.has_password === false

  const rateLimitError = (): string | null => {
    const now = Date.now()
    const withinWindow = now - attempts.lastAt < ATTEMPT_WINDOW_MS
    if (withinWindow && attempts.count >= MAX_ATTEMPTS) {
      const remainingMinutes = Math.ceil((ATTEMPT_WINDOW_MS - (now - attempts.lastAt)) / 1000 / 60)
      return `Too many attempts. Please wait ${remainingMinutes} minutes before trying again.`
    }
    setAttempts({ count: (withinWindow ? attempts.count : 0) + 1, lastAt: now })
    return null
  }

  const validationError = (): string | null => {
    if (!passwords.newPassword) return null
    if (!passwordStrength.meetsRequirements) return 'Password does not meet security requirements'
    if (passwords.newPassword !== passwords.confirmPassword) return 'New passwords do not match'
    if (passwords.newPassword === passwords.currentPassword) return 'New password must be different from current password'
    if (!isSetPassword && !passwords.currentPassword) return 'Current password is required to change password'
    return null
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()

    const limited = rateLimitError()
    if (limited) {
      setMessage({ type: 'error', text: limited })
      return
    }

    const invalid = validationError()
    if (invalid) {
      setMessage({ type: 'error', text: invalid })
      return
    }

    const newEmail = email.trim()
    const emailChanged = newEmail !== user.email
    const update: UserProfileUpdate = {}
    if (username !== user.username) update.username = username
    if (passwords.newPassword) {
      if (!isSetPassword) update.current_password = passwords.currentPassword
      update.new_password = passwords.newPassword
    }
    const profileChanged = Object.keys(update).length > 0
    if (!profileChanged && !emailChanged) {
      setMessage({ type: 'warning', text: 'No changes to save' })
      return
    }
    if (passwords.newPassword && !confirm('Change your password? You will be signed out on your other devices.')) {
      return
    }

    setIsLoading(true)
    setMessage(null)
    try {
      const outcomes: string[] = []
      if (profileChanged) {
        onUserUpdate(await api.updateProfileSettings(update))
        setPasswords(EMPTY_PASSWORDS)
        outcomes.push(passwords.newPassword ? 'Profile updated. Your password has been changed and your other devices were signed out.' : 'Profile updated.')
      }
      if (emailChanged) {
        await api.sendEmailChangeVerification(newEmail)
        outcomes.push(`We sent a link to ${newEmail}. Your email changes once you open it.`)
      }
      setMessage({ type: 'success', text: outcomes.join(' ') })
      setAttempts({ count: 0, lastAt: 0 })
    } catch (error) {
      setMessage({ type: 'error', text: (error instanceof Error && error.message) || 'Failed to update profile. Please try again later.' })
    } finally {
      setIsLoading(false)
    }
  }

  const setPassword = (field: keyof typeof EMPTY_PASSWORDS) => (value: string) =>
    setPasswords((current) => ({ ...current, [field]: value }))

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <UsernameField value={username} onChange={setUsername} status={usernameStatus} />

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" aria-describedby="email-hint" />
        <p id="email-hint" className="text-caption text-muted-foreground">
          To change it, we email a confirmation link to the new address.
        </p>
      </div>

      <fieldset className="space-y-4">
        <legend className="mb-2 text-body font-semibold text-foreground">{isSetPassword ? 'Set a password' : 'Change password'}</legend>
        {!isSetPassword && (
          <PasswordField
            id="currentPassword"
            label="Current password"
            value={passwords.currentPassword}
            onChange={setPassword('currentPassword')}
            placeholder="Enter current password"
            autoComplete="current-password"
          />
        )}
        <PasswordField
          id="newPassword"
          label="New password"
          value={passwords.newPassword}
          onChange={setPassword('newPassword')}
          placeholder="Enter new password"
          autoComplete="new-password"
          hint={isSetPassword ? 'You signed in with Google, so no current password is needed.' : undefined}
        >
          {passwords.newPassword && <PasswordStrengthMeter strength={passwordStrength} />}
        </PasswordField>
        <PasswordField
          id="confirmPassword"
          label="Confirm new password"
          value={passwords.confirmPassword}
          onChange={setPassword('confirmPassword')}
          placeholder="Confirm new password"
          autoComplete="new-password"
        />
      </fieldset>

      {message && <Alert variant={message.type}>{message.text}</Alert>}

      <div className="flex justify-end">
        <Button type="submit" disabled={isLoading || (!!passwords.newPassword && !passwordStrength.meetsRequirements)}>
          {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
          {isLoading ? 'Saving...' : 'Save changes'}
        </Button>
      </div>
    </form>
  )
}

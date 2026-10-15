'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export interface UsernameStatus {
  checking: boolean
  available: boolean | null
  message: string
}

const IDLE: UsernameStatus = { checking: false, available: null, message: '' }
const DEBOUNCE_MS = 500
const USERNAME_PATTERN = /^[a-zA-Z0-9_-]+$/

export function useUsernameAvailability(username: string, currentUsername: string): UsernameStatus {
  const [status, setStatus] = useState<UsernameStatus>(IDLE)

  useEffect(() => {
    const check = async () => {
      if (!username || username === currentUsername) {
        setStatus(IDLE)
        return
      }
      if (username.length < 3) {
        setStatus({ checking: false, available: false, message: 'Username must be at least 3 characters' })
        return
      }
      if (!USERNAME_PATTERN.test(username)) {
        setStatus({ checking: false, available: false, message: 'Username can only contain letters, numbers, underscores, and hyphens' })
        return
      }
      setStatus({ checking: true, available: null, message: 'Checking availability...' })
      try {
        const result = await api.checkUsernameAvailability(username)
        setStatus({
          checking: false,
          available: result.available,
          message: result.available ? 'Username available' : 'Username already taken',
        })
      } catch {
        setStatus({ checking: false, available: false, message: 'Error checking username' })
      }
    }

    const timeoutId = setTimeout(check, DEBOUNCE_MS)
    return () => clearTimeout(timeoutId)
  }, [username, currentUsername])

  return status
}

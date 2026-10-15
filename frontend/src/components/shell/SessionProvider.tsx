'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, APIError, type CourseListItem, type User } from '@/lib/api'
import { Spinner } from '@/components/ui/spinner'

interface SessionValue {
  user: User
  setUser: (user: User) => void
  courses: CourseListItem[] | null
  coursesError: string | null
  reloadCourses: () => Promise<void>
  logout: () => void
}

const SessionContext = createContext<SessionValue | null>(null)

export function useSession(): SessionValue {
  const value = useContext(SessionContext)
  if (!value) throw new Error('useSession must be used inside SessionProvider')
  return value
}

function readCachedUser(): User | null {
  try {
    const raw = localStorage.getItem('user')
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

function cacheUser(user: User) {
  localStorage.setItem('user', JSON.stringify(user))
}

function redirectToLanding() {
  window.location.replace('/landing')
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null)
  const [courses, setCourses] = useState<CourseListItem[] | null>(null)
  const [coursesError, setCoursesError] = useState<string | null>(null)

  const setUser = useCallback((next: User) => {
    cacheUser(next)
    setUserState(next)
  }, [])

  const reloadCourses = useCallback(async () => {
    try {
      setCourses(await api.getCourses())
      setCoursesError(null)
    } catch (error) {
      setCoursesError(error instanceof APIError ? error.message : 'Could not load courses')
    }
  }, [])

  const logout = useCallback(() => {
    api.clearToken()
    redirectToLanding()
  }, [])

  useEffect(() => {
    if (!api.hasToken()) {
      redirectToLanding()
      return
    }
    const cached = readCachedUser()
    if (cached) setUserState(cached)
    api.getProfileSettings()
      .then(setUser)
      .catch((error) => {
        if (!cached || (error instanceof APIError && error.status === 401)) {
          api.clearToken()
          redirectToLanding()
        }
      })
    reloadCourses()
  }, [setUser, reloadCourses])

  const value = useMemo(
    () => (user ? { user, setUser, courses, coursesError, reloadCourses, logout } : null),
    [user, setUser, courses, coursesError, reloadCourses, logout]
  )

  if (!value) {
    return (
      <div className="flex h-dvh items-center justify-center bg-background">
        <Spinner label="Loading StudentsAI" />
      </div>
    )
  }

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

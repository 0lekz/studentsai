'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, APIError, type Course } from '@/lib/api'
import { useSession } from '@/components/shell/SessionProvider'

type CourseState =
  | { status: 'loading' }
  | { status: 'missing' }
  | { status: 'error'; message: string }
  | { status: 'ready'; course: Course }

interface CourseValue {
  course: Course
  reloadCourse: () => Promise<void>
}

const CourseContext = createContext<CourseValue | null>(null)

export function useCourse(): CourseValue {
  const value = useContext(CourseContext)
  if (!value) throw new Error('useCourse must be used inside CourseProvider')
  return value
}

export function useCourseState(courseId: string) {
  const { courses } = useSession()
  const listed = courses?.find((course) => course.id === courseId)
  const [state, setState] = useState<CourseState>(listed ? { status: 'ready', course: listed } : { status: 'loading' })

  const reloadCourse = useCallback(async () => {
    try {
      setState({ status: 'ready', course: await api.getCourse(courseId) })
    } catch (error) {
      if (error instanceof APIError && (error.status === 404 || error.status === 422)) {
        setState({ status: 'missing' })
      } else {
        setState({ status: 'error', message: error instanceof Error ? error.message : 'Could not load the course' })
      }
    }
  }, [courseId])

  useEffect(() => {
    if (listed) {
      setState({ status: 'ready', course: listed })
    } else {
      reloadCourse()
    }
  }, [listed, reloadCourse])

  return { state, reloadCourse }
}

export function CourseProvider({ value, children }: { value: CourseValue; children: React.ReactNode }) {
  return <CourseContext.Provider value={value}>{children}</CourseContext.Provider>
}

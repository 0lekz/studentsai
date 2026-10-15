'use client'

import { Suspense } from 'react'
import { NotesWorkspace } from '@/components/notes/NotesWorkspace'
import { useCourse } from '@/components/course/CourseProvider'
import { Spinner } from '@/components/ui/spinner'

export default function NotesPage() {
  const { course } = useCourse()
  return (
    <Suspense fallback={<Spinner className="flex-1" label="Loading notes" />}>
      <NotesWorkspace courseId={course.id} />
    </Suspense>
  )
}

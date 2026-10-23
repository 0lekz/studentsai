'use client'

import { Suspense } from 'react'
import { useCourse } from '@/components/course/CourseProvider'
import { PracticeView } from '@/components/practice/PracticeView'
import { Spinner } from '@/components/ui/spinner'

export default function PracticePage() {
  const { course } = useCourse()
  return (
    <Suspense fallback={<Spinner className="flex-1" label="Loading practice" />}>
      <PracticeView courseId={course.id} />
    </Suspense>
  )
}

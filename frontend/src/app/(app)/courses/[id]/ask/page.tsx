'use client'

import { AskView } from '@/components/ask/AskView'
import { useCourse } from '@/components/course/CourseProvider'

export default function AskPage() {
  const { course } = useCourse()
  return <AskView courseId={course.id} courseName={course.name} />
}

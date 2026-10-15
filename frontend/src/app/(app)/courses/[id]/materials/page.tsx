'use client'

import { MaterialsView } from '@/components/materials/MaterialsView'
import { useCourse } from '@/components/course/CourseProvider'

export default function MaterialsPage() {
  const { course } = useCourse()
  return <MaterialsView courseId={course.id} />
}

'use client'

import { useCourse } from '@/components/course/CourseProvider'
import { ConceptMapView } from '@/components/graph/ConceptMapView'

export default function MapPage() {
  const { course } = useCourse()
  return <ConceptMapView courseId={course.id} />
}

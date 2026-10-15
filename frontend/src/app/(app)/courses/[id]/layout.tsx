'use client'

import Link from 'next/link'
import { useParams, usePathname } from 'next/navigation'
import { BookX } from 'lucide-react'
import { CourseHeader } from '@/components/course/CourseHeader'
import { CourseProvider, useCourseState } from '@/components/course/CourseProvider'
import { CourseSectionBar } from '@/components/course/CourseSectionNav'
import { activeSectionFrom } from '@/components/course/sections'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'

export default function CourseLayout({ children }: { children: React.ReactNode }) {
  const { id } = useParams<{ id: string }>()
  const pathname = usePathname()
  const { state, reloadCourse } = useCourseState(id)

  if (state.status === 'loading') return <Spinner className="flex-1" label="Loading course" />

  if (state.status === 'missing') {
    return (
      <EmptyState icon={BookX} title="Course not found" description="It may have been deleted, or the link is wrong.">
        <Button asChild>
          <Link href="/today">Go to Today</Link>
        </Button>
      </EmptyState>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="p-gutter">
        <Alert variant="error">{state.message}</Alert>
      </div>
    )
  }

  const activeSection = activeSectionFrom(pathname)

  return (
    <CourseProvider value={{ course: state.course, reloadCourse }}>
      <div className="flex min-h-0 flex-1 flex-col">
        <CourseHeader course={state.course} activeSection={activeSection} onCourseChanged={reloadCourse} />
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        <div className="md:hidden">
          <CourseSectionBar courseId={state.course.id} active={activeSection} />
        </div>
      </div>
    </CourseProvider>
  )
}

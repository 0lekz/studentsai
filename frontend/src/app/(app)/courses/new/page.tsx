'use client'

import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { CourseForm } from '@/components/course/CourseForm'
import { useSession } from '@/components/shell/SessionProvider'

export default function NewCoursePage() {
  const router = useRouter()
  const { reloadCourses } = useSession()

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-prose px-gutter py-section">
        <h1 className="text-headline font-semibold text-foreground">Add a course</h1>
        <p className="mt-1 text-body text-muted-foreground">
          A course holds its slides, notes and practice. You can change these details later.
        </p>
        <div className="mt-8 rounded-card border border-border bg-surface p-6 shadow-sm">
          <CourseForm
            submitLabel="Create course"
            onCancel={() => router.back()}
            onSubmit={async (values) => {
              const course = await api.createCourse(values)
              await reloadCourses()
              router.push(`/courses/${course.id}/materials`)
            }}
          />
        </div>
      </div>
    </div>
  )
}

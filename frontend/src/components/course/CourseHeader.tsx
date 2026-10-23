import type { Course } from '@/lib/api'
import { formatExamCountdown, formatShortDate } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { CourseActions } from './CourseActions'
import { CourseSectionTabs } from './CourseSectionNav'
import type { CourseSectionSlug } from './sections'

interface CourseHeaderProps {
  course: Course
  activeSection?: CourseSectionSlug
  onCourseChanged: () => Promise<void>
}

export function CourseHeader({ course, activeSection, onCourseChanged }: CourseHeaderProps) {
  const meta = [
    course.term,
    course.exam_date ? `${formatExamCountdown(course.exam_date)} (${formatShortDate(course.exam_date)})` : null,
  ].filter(Boolean)

  return (
    <header className="shrink-0 border-b border-border bg-surface px-gutter">
      <div className="flex items-start justify-between gap-4 pb-3 pt-4 md:pb-1 md:pt-6">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-title font-semibold text-foreground md:text-headline">{course.name}</h1>
            {course.archived && <Badge variant="secondary">Archived</Badge>}
          </div>
          {meta.length > 0 && <p className="mt-0.5 truncate text-body text-muted-foreground">{meta.join(' · ')}</p>}
        </div>
        <CourseActions course={course} onChanged={onCourseChanged} />
      </div>
      <div className="hidden md:block">
        <CourseSectionTabs courseId={course.id} active={activeSection} />
      </div>
    </header>
  )
}

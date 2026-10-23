import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import type { CourseListItem } from '@/lib/api'
import { daysUntil, formatExamCountdown, pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'

function CourseCounts({ course }: { course: CourseListItem }) {
  return (
    <span className="truncate">
      {[pluralize(course.documents_count, 'file'), pluralize(course.notes_count, 'note'), pluralize(course.flashcards_count, 'flashcard')].join(' · ')}
    </span>
  )
}

export function CourseSummaryList({ courses }: { courses: CourseListItem[] }) {
  return (
    <ul className="divide-y divide-border overflow-hidden rounded-card border border-border bg-surface">
      {courses.map((course) => {
        const examSoon = course.exam_date !== null && daysUntil(course.exam_date) >= 0 && daysUntil(course.exam_date) <= 14
        return (
          <li key={course.id}>
            <Link
              href={`/courses/${course.id}/materials`}
              className="flex items-center gap-4 px-4 py-3 transition-colors hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-body font-medium text-foreground">{course.name}</p>
                <p className="flex gap-1 text-caption text-muted-foreground">
                  <CourseCounts course={course} />
                </p>
              </div>
              {course.exam_date && (
                <span className={cn('shrink-0 text-caption font-medium', examSoon ? 'text-brand-soft-foreground' : 'text-muted-foreground')}>
                  {formatExamCountdown(course.exam_date)}
                </span>
              )}
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
            </Link>
          </li>
        )
      })}
    </ul>
  )
}

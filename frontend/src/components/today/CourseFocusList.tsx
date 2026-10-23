import Link from 'next/link'
import { Layers, Network } from 'lucide-react'
import type { CourseListItem, TodayCourse } from '@/lib/api'
import { daysUntil, formatExamCountdown, pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MasteryMeter } from '@/components/concepts/MasteryMeter'

const EXAM_SOON_DAYS = 14

function WeakConcepts({ course, focus }: { course: CourseListItem; focus: TodayCourse | undefined }) {
  if (focus && focus.weakest_concepts.length > 0) {
    return (
      <ul aria-label={`Weakest concepts in ${course.name}`} className="space-y-2">
        {focus.weakest_concepts.map((concept) => (
          <li key={concept.id} className="flex items-center gap-3">
            <span className="min-w-0 flex-1 truncate text-body text-foreground">{concept.name}</span>
            <MasteryMeter mastery={concept.mastery} />
          </li>
        ))}
      </ul>
    )
  }
  return (
    <p className="text-body text-muted-foreground">
      {course.documents_count === 0 ? 'No files yet. Add slides to start practicing.' : 'Practice a session and the concepts you know least show up here.'}
    </p>
  )
}

export function CourseFocusList({ courses, focus }: { courses: CourseListItem[]; focus: TodayCourse[] | null }) {
  return (
    <ul className="grid gap-4 md:grid-cols-2">
      {courses.map((course) => {
        const courseFocus = focus?.find((entry) => entry.course.id === course.id)
        const examDays = course.exam_date ? daysUntil(course.exam_date) : null
        return (
          <li key={course.id} className="flex flex-col rounded-card border border-border bg-surface p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <Link href={`/courses/${course.id}/materials`} className="block truncate text-body-lg font-semibold text-foreground hover:underline">
                  {course.name}
                </Link>
                <p className="text-caption text-muted-foreground">
                  {[pluralize(course.documents_count, 'file'), course.exam_date ? formatExamCountdown(course.exam_date) : course.term].filter(Boolean).join(' · ')}
                </p>
              </div>
              {courseFocus && courseFocus.due_count > 0 ? (
                <Badge variant="brand" className="shrink-0">
                  {courseFocus.due_count} due
                </Badge>
              ) : examDays !== null && examDays >= 0 && examDays <= EXAM_SOON_DAYS ? (
                <Badge variant="warning" className="shrink-0">
                  Exam soon
                </Badge>
              ) : null}
            </div>

            <div className="mt-4 flex-1">
              <h3 className="mb-2 text-caption font-medium uppercase tracking-wide text-muted-foreground">Weakest concepts</h3>
              {focus === null ? (
                <div aria-hidden className="space-y-2">
                  {[0, 1, 2].map((row) => (
                    <div key={row} className={cn('h-4 animate-pulse rounded-full bg-muted', row === 1 ? 'w-3/4' : 'w-5/6')} />
                  ))}
                </div>
              ) : (
                <WeakConcepts course={course} focus={courseFocus} />
              )}
            </div>

            <div className="mt-4 flex gap-2 border-t border-border pt-3">
              <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link href={`/courses/${course.id}/practice`}>
                  <Layers className="h-4 w-4" />
                  Practice
                </Link>
              </Button>
              <Button asChild variant="ghost" size="sm">
                <Link href={`/courses/${course.id}/map`}>
                  <Network className="h-4 w-4" />
                  Map
                </Link>
              </Button>
            </div>
          </li>
        )
      })}
    </ul>
  )
}

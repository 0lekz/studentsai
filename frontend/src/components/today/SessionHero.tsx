import Link from 'next/link'
import { CalendarCheck, FileText, Play } from 'lucide-react'
import type { CourseListItem, TodaySummary } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

interface SessionHeroProps {
  today: TodaySummary | null
  error: string | null
  courses: CourseListItem[]
  onRetry: () => void
}

function HeroFrame({ title, description, action, children }: { title: string; description: string; action?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <section aria-labelledby="hero-title" className="mt-8 rounded-card border border-border bg-surface p-6 shadow-sm">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-card bg-brand-soft text-brand-soft-foreground">
            <CalendarCheck className="h-6 w-6" aria-hidden />
          </div>
          <div className="min-w-0">
            <h2 id="hero-title" className="text-title font-semibold text-foreground">
              {title}
            </h2>
            <p className="text-body text-muted-foreground">{description}</p>
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children}
    </section>
  )
}

export function SessionHero({ today, error, courses, onRetry }: SessionHeroProps) {
  if (error && !today) {
    return (
      <HeroFrame title="Today’s session" description="Your reviews could not be loaded.">
        <Alert variant="error" className="mt-4 flex items-center justify-between gap-3">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={onRetry} className="shrink-0">
            Try again
          </Button>
        </Alert>
      </HeroFrame>
    )
  }

  if (!today) {
    return (
      <HeroFrame title="Checking your reviews" description="Lining up what is due across your courses.">
        <div aria-hidden className="mt-5 h-11 w-full animate-pulse rounded-control bg-muted sm:ml-auto sm:w-40" />
      </HeroFrame>
    )
  }

  const suggestedCourse = today.suggested ? courses.find((course) => course.id === today.suggested?.course_id) : undefined
  if (today.suggested) {
    const { course_id, size } = today.suggested
    return (
      <HeroFrame
        title={today.due_count > 0 ? `${pluralize(today.due_count, 'review')} due` : 'Ready for today’s session'}
        description={`${suggestedCourse ? `${suggestedCourse.name}, ` : ''}${pluralize(size, 'question')}. Due reviews first, then your weakest concepts.`}
        action={
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link href={`/courses/${course_id}/practice?start=1&size=${size}`}>
              <Play className="h-4 w-4" />
              Start session
            </Link>
          </Button>
        }
      />
    )
  }

  const withoutFiles = courses.find((course) => course.documents_count === 0)
  if (withoutFiles) {
    return (
      <HeroFrame
        title="Drop in your slides"
        description={`Add lecture slides or PDFs to ${withoutFiles.name} and Today will line up a session from them.`}
        action={
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link href={`/courses/${withoutFiles.id}/materials`}>
              <FileText className="h-4 w-4" />
              Add files
            </Link>
          </Button>
        }
      />
    )
  }

  return <HeroFrame title="All caught up" description="Nothing is due right now. Come back tomorrow, or practice a course below." />
}

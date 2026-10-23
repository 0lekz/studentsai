'use client'

import Link from 'next/link'
import { FileText, GraduationCap, Layers, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useSession } from '@/components/shell/SessionProvider'
import { CourseFocusList } from './CourseFocusList'
import { SessionHero } from './SessionHero'
import { useToday } from './useToday'

const ONBOARDING_STEPS = [
  { icon: GraduationCap, title: 'Add a course', description: 'One per class you are taking, with its exam date if you know it.' },
  { icon: FileText, title: 'Drop in the slides', description: 'Lecture slides and PDFs become concepts and practice questions.' },
  { icon: Layers, title: 'Practice daily', description: 'Twenty minutes a day, with feedback that cites your slides.' },
]

function todayLabel(): string {
  return new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
}

function Onboarding() {
  return (
    <section aria-labelledby="onboarding-title" className="mt-8 rounded-card border border-border bg-surface p-6 shadow-sm sm:p-8">
      <h2 id="onboarding-title" className="text-title font-semibold text-foreground">
        Start with a course
      </h2>
      <p className="mt-1 text-body text-muted-foreground">StudentsAI works from your own course material. Three steps and Today lines up your first session.</p>
      <ol className="mt-6 grid gap-4 sm:grid-cols-3">
        {ONBOARDING_STEPS.map(({ icon: Icon, title, description }, index) => (
          <li key={title} className="rounded-card bg-muted p-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-brand-soft-foreground">
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <span className="text-caption font-medium text-muted-foreground">Step {index + 1}</span>
            </div>
            <p className="mt-3 text-body font-semibold text-foreground">{title}</p>
            <p className="mt-1 text-body text-muted-foreground">{description}</p>
          </li>
        ))}
      </ol>
      <Button asChild size="lg" className="mt-6 w-full sm:w-auto">
        <Link href="/courses/new">
          <Plus className="h-4 w-4" />
          Add course
        </Link>
      </Button>
    </section>
  )
}

export function TodayView() {
  const { user, courses } = useSession()
  const { today, error, reload } = useToday()
  const activeCourses = courses?.filter((course) => !course.archived) ?? []

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-content px-gutter py-section">
        <p className="text-body text-muted-foreground">{todayLabel()}</p>
        <h1 className="mt-1 break-words text-headline font-semibold text-foreground md:text-display">Hi {user.username}</h1>

        {courses === null ? (
          <Spinner label="Loading your courses" />
        ) : activeCourses.length === 0 ? (
          <Onboarding />
        ) : (
          <>
            <SessionHero today={today} error={error} courses={activeCourses} onRetry={reload} />
            <section aria-labelledby="courses-title" className="mt-section">
              <h2 id="courses-title" className="mb-3 text-body font-semibold text-foreground">
                Your courses
              </h2>
              <CourseFocusList courses={activeCourses} focus={today?.courses ?? (error ? [] : null)} />
            </section>
          </>
        )}
      </div>
    </div>
  )
}

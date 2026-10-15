'use client'

import Link from 'next/link'
import { useState } from 'react'
import { CalendarCheck, GraduationCap, Play, Plus } from 'lucide-react'
import { api, type Flashcard } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'
import { StudySession } from '@/components/flashcards/StudySession'
import { useSession } from '@/components/shell/SessionProvider'
import { CourseSummaryList } from './CourseSummaryList'
import { useDueFlashcards } from './useDueFlashcards'

const rateFlashcard = (card: Flashcard, quality: number) => api.reviewFlashcard(card.id, quality)

function todayLabel(): string {
  return new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
}

export function TodayView() {
  const { user, courses } = useSession()
  const { due, error, reload } = useDueFlashcards()
  const [session, setSession] = useState<Flashcard[] | null>(null)

  const activeCourses = courses?.filter((course) => !course.archived) ?? []
  const dueCount = due?.length ?? 0

  if (session) {
    return (
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="px-gutter py-section">
          <StudySession
            cards={session}
            onRate={rateFlashcard}
            onExit={() => {
              setSession(null)
              reload()
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-content px-gutter py-section">
        <p className="text-body text-muted-foreground">{todayLabel()}</p>
        <h1 className="mt-1 text-headline font-semibold text-foreground md:text-display">Hi {user.username}</h1>

        {courses === null ? (
          <Spinner label="Loading your courses" />
        ) : activeCourses.length === 0 ? (
          <div className="mt-8 rounded-card border border-border bg-surface">
            <EmptyState
              icon={GraduationCap}
              title="Start with a course"
              description="Add a course, drop in its slides, and Today will line up what to review."
            >
              <Button asChild size="lg">
                <Link href="/courses/new">
                  <Plus className="h-4 w-4" />
                  Add course
                </Link>
              </Button>
            </EmptyState>
          </div>
        ) : (
          <>
            <section aria-labelledby="due-title" className="mt-8 rounded-card border border-border bg-surface p-6 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-card bg-brand-soft text-brand-soft-foreground">
                    <CalendarCheck className="h-6 w-6" aria-hidden />
                  </div>
                  <div>
                    <h2 id="due-title" className="text-title font-semibold text-foreground">
                      {due === null ? 'Checking your reviews...' : dueCount > 0 ? `${pluralize(dueCount, 'review')} due` : 'Nothing due right now'}
                    </h2>
                    <p className="text-body text-muted-foreground">
                      {dueCount > 0 ? 'Cards you reviewed before, scheduled for today across all courses.' : 'Practice a course to build up your review queue.'}
                    </p>
                  </div>
                </div>
                <Button size="lg" disabled={dueCount === 0} onClick={() => due && setSession(due)} className="w-full sm:w-auto">
                  <Play className="h-4 w-4" />
                  Start session
                </Button>
              </div>
              {error && (
                <Alert variant="error" className="mt-4">
                  {error}
                </Alert>
              )}
            </section>

            <section aria-labelledby="courses-title" className="mt-section">
              <h2 id="courses-title" className="mb-3 text-body font-semibold text-foreground">
                Your courses
              </h2>
              <CourseSummaryList courses={activeCourses} />
            </section>
          </>
        )}
      </div>
    </div>
  )
}

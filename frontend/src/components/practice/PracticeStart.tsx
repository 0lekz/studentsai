import Link from 'next/link'
import { FileText, Layers, Network, Play } from 'lucide-react'
import type { Concept } from '@/lib/api'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'
import { MasteryMeter } from '@/components/concepts/MasteryMeter'
import type { CourseReadiness } from './useCourseReadiness'
import { SessionLengthPicker } from './SessionLengthPicker'

const FOCUS_COUNT = 4

function weakest(concepts: Concept[]): Concept[] {
  return [...concepts].sort((a, b) => (a.mastery ?? -1) - (b.mastery ?? -1) || a.order - b.order).slice(0, FOCUS_COUNT)
}

function FocusConcepts({ courseId, concepts }: { courseId: string; concepts: Concept[] }) {
  if (concepts.length === 0) {
    return (
      <p className="text-body text-muted-foreground">
        Extract concepts in{' '}
        <Link href={`/courses/${courseId}/materials`} className="font-medium text-primary underline-offset-4 hover:underline">
          Materials
        </Link>{' '}
        and sessions will focus on the ones you know least.
      </p>
    )
  }
  return (
    <ul className="divide-y divide-border overflow-hidden rounded-card border border-border bg-surface">
      {weakest(concepts).map((concept) => (
        <li key={concept.id}>
          <Link
            href={`/courses/${courseId}/practice?concept=${concept.id}`}
            className="flex items-center gap-4 px-4 py-3 transition-colors hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
          >
            <span className="min-w-0 flex-1 truncate text-body font-medium text-foreground">{concept.name}</span>
            <MasteryMeter mastery={concept.mastery} />
          </Link>
        </li>
      ))}
    </ul>
  )
}

interface PracticeStartProps {
  courseId: string
  readiness: CourseReadiness
  size: number
  onSizeChange: (size: number) => void
  error?: string
  notice?: string
  onStart: () => void
}

export function PracticeStart({ courseId, readiness, size, onSizeChange, error, notice, onStart }: PracticeStartProps) {
  const { documents, concepts } = readiness

  if (readiness.error) return <Alert variant="error">{readiness.error}</Alert>
  if (documents === null) return <Spinner label="Loading practice" />

  const readyDocuments = documents.filter((document) => document.status === 'ready')
  if (readyDocuments.length === 0) {
    const processing = documents.some((document) => document.status === 'pending')
    return (
      <EmptyState
        icon={Layers}
        title={processing ? 'Your files are still processing' : 'Add your slides first'}
        description={
          processing
            ? 'Questions are written from your files once they finish processing. This usually takes a few seconds.'
            : 'Questions are written from this course’s slides and PDFs, and every answer points back to the page it comes from.'
        }
      >
        <Button asChild size="lg" className="w-full sm:w-auto">
          <Link href={`/courses/${courseId}/materials`}>
            <FileText className="h-4 w-4" />
            Open materials
          </Link>
        </Button>
      </EmptyState>
    )
  }

  return (
    <div className="space-y-section">
      <section aria-labelledby="practice-title" className="rounded-card border border-border bg-surface p-6 shadow-sm sm:p-8">
        <div className="flex h-12 w-12 items-center justify-center rounded-card bg-brand-soft text-brand-soft-foreground">
          <Layers className="h-6 w-6" aria-hidden />
        </div>
        <h2 id="practice-title" className="mt-4 text-headline font-semibold text-foreground">
          Practice session
        </h2>
        <p className="mt-1 text-body-lg text-muted-foreground">
          One question at a time, with feedback that points to the page the answer comes from. Due reviews come first, then your weakest concepts.
        </p>
        {error && (
          <Alert variant="error" className="mt-5">
            {error}
          </Alert>
        )}
        {notice && (
          <Alert variant="warning" className="mt-5">
            {notice}
          </Alert>
        )}
        <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <SessionLengthPicker value={size} onChange={onSizeChange} />
            <span className="text-body text-muted-foreground">questions</span>
          </div>
          <Button size="lg" onClick={onStart} className="w-full sm:w-auto">
            <Play className="h-4 w-4" />
            Start session
          </Button>
        </div>
      </section>

      <section aria-labelledby="focus-title">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 id="focus-title" className="text-body font-semibold text-foreground">
            Needs the most work
          </h2>
          {concepts && concepts.length > 0 && (
            <Button asChild variant="ghost" size="sm" className="text-muted-foreground">
              <Link href={`/courses/${courseId}/map`}>
                <Network className="h-4 w-4" />
                Open map
              </Link>
            </Button>
          )}
        </div>
        {concepts === null ? <Spinner className="py-6" label="Loading concepts" /> : <FocusConcepts courseId={courseId} concepts={concepts} />}
      </section>
    </div>
  )
}

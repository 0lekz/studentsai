'use client'

import { useEffect, useRef, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import type { Citation } from '@/lib/api'
import { SourcePanel } from '@/components/citations/SourcePanel'
import { summarize } from './outcome'
import { PracticeStart } from './PracticeStart'
import { QuestionStep } from './QuestionStep'
import { SessionScreen } from './SessionScreen'
import { SessionSummary } from './SessionSummary'
import { useCourseReadiness } from './useCourseReadiness'
import { DEFAULT_SESSION_SIZE, usePracticeSession, type SessionRequest } from './usePracticeSession'

function requestFromParams(params: URLSearchParams): SessionRequest | null {
  const conceptId = params.get('concept') ?? undefined
  if (!conceptId && params.get('start') === null) return null
  const size = Number(params.get('size'))
  return { conceptId, size: Number.isInteger(size) && size > 0 ? size : undefined }
}

const EMPTY_SESSION_NOTICE = 'No questions could be written from these files yet. Try again in a moment, or add more material.'

const summaryProgress = (total: number, answered: number) => ({ done: answered, total, position: answered })

export function PracticeView({ courseId }: { courseId: string }) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const readiness = useCourseReadiness(courseId)
  const { state, start, record, next, end, reset } = usePracticeSession(courseId)
  const [size, setSize] = useState(DEFAULT_SESSION_SIZE)
  const [source, setSource] = useState<Citation | null>(null)
  const lastRequest = useRef<SessionRequest>({})
  const handledParams = useRef<string | null>(null)

  const begin = (request: SessionRequest) => {
    lastRequest.current = request
    start(request)
  }

  useEffect(() => {
    const key = searchParams.toString()
    if (handledParams.current === key) return
    handledParams.current = key
    const request = requestFromParams(searchParams)
    if (!request) return
    lastRequest.current = request
    start(request)
    router.replace(pathname, { scroll: false })
  }, [searchParams, start, router, pathname])

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-prose px-gutter py-section">
        <PracticeStart
          courseId={courseId}
          readiness={readiness}
          size={size}
          onSizeChange={setSize}
          error={state.status === 'idle' ? state.error : undefined}
          notice={state.status === 'empty' ? EMPTY_SESSION_NOTICE : undefined}
          onStart={() => begin({ size })}
        />
      </div>

      {state.status === 'loading' && (
        <SessionScreen onEnd={reset}>
          <div role="status" className="flex flex-1 flex-col items-center justify-center gap-3 px-gutter text-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden />
            <p className="text-body-lg font-medium text-foreground">Picking your questions</p>
            <p className="max-w-sm text-body text-muted-foreground">Due reviews first. New questions are written from your slides, which can take a few seconds.</p>
          </div>
        </SessionScreen>
      )}

      {state.status === 'active' && (
        <SessionScreen
          onEnd={end}
          progress={{
            done: Object.keys(state.outcomes).length,
            total: state.questions.length,
            position: state.index + 1,
          }}
        >
          <QuestionStep
            key={state.questions[state.index].id}
            courseId={courseId}
            question={state.questions[state.index]}
            isLast={state.index === state.questions.length - 1}
            onOutcome={(outcome) => record(state.questions[state.index].id, outcome)}
            onNext={next}
            onOpenSource={setSource}
          />
        </SessionScreen>
      )}

      {state.status === 'summary' && (
        <SessionScreen onEnd={reset} progress={summaryProgress(state.questions.length, Object.keys(state.outcomes).length)}>
          <SessionSummary summary={summarize(state.questions, state.outcomes)} onPracticeMore={() => begin(lastRequest.current)} onDone={() => router.push('/today')} />
        </SessionScreen>
      )}

      <SourcePanel citation={source} onClose={() => setSource(null)} />
    </div>
  )
}

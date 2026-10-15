'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { api, type Citation, type Concept } from '@/lib/api'
import { SourcePanel } from '@/components/citations/SourcePanel'
import { AskAnswer } from './AskAnswer'
import { AskComposer } from './AskComposer'
import { AskIntro } from './AskIntro'
import { useAskThread } from './useAskThread'

function suggestionsFrom(concepts: Concept[]): string[] {
  const [first, second, third] = [...concepts].sort((a, b) => (a.mastery ?? -1) - (b.mastery ?? -1) || a.order - b.order)
  return [
    first && `Explain ${first.name} in simple terms`,
    first && second && `How does ${first.name} relate to ${second.name}?`,
    third && `What should I remember about ${third.name}?`,
  ].filter((suggestion): suggestion is string => Boolean(suggestion))
}

export function AskView({ courseId, courseName }: { courseId: string; courseName: string }) {
  const { exchanges, ask, retry, pending } = useAskThread(courseId)
  const [draft, setDraft] = useState('')
  const [source, setSource] = useState<Citation | null>(null)
  const [concepts, setConcepts] = useState<Concept[]>([])
  const thread = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.getConcepts(courseId).then(setConcepts).catch(() => setConcepts([]))
  }, [courseId])

  useEffect(() => {
    thread.current?.lastElementChild?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }, [exchanges.length])

  const suggestions = useMemo(() => suggestionsFrom(concepts), [concepts])

  const send = (question: string) => {
    ask(question.trim())
    setDraft('')
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        {exchanges.length === 0 ? (
          <AskIntro courseName={courseName} suggestions={suggestions} onSuggestion={send} />
        ) : (
          <div ref={thread} className="mx-auto w-full max-w-prose space-y-10 px-gutter py-section">
            {exchanges.map((exchange) => (
              <AskAnswer key={exchange.id} exchange={exchange} courseId={courseId} onRetry={() => retry(exchange)} onOpenSource={setSource} />
            ))}
          </div>
        )}
      </div>
      <AskComposer value={draft} onChange={setDraft} onSubmit={() => send(draft)} busy={pending} />
      <SourcePanel citation={source} onClose={() => setSource(null)} />
    </div>
  )
}

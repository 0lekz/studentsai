import Link from 'next/link'
import { FileSearch, RotateCcw } from 'lucide-react'
import type { AskResult, Citation } from '@/lib/api'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Markdown } from '@/components/ui/markdown'
import { CitationChip } from '@/components/citations/CitationChip'
import type { Exchange } from './useAskThread'

function NotCovered({ answer, courseId }: { answer: string; courseId: string }) {
  return (
    <div className="rounded-card border border-border bg-surface p-5">
      <p className="flex items-center gap-2 text-body-lg font-semibold text-foreground">
        <FileSearch className="h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
        Not in your materials
      </p>
      <p className="mt-2 text-body-lg text-muted-foreground">{answer}</p>
      <Button asChild variant="link" className="mt-2 h-auto px-0">
        <Link href={`/courses/${courseId}/materials`}>Add the slides that cover it</Link>
      </Button>
    </div>
  )
}

function GroundedAnswer({ result, onOpenSource }: { result: AskResult; onOpenSource: (citation: Citation) => void }) {
  return (
    <div>
      <Markdown
        source={result.answer}
        citationCount={result.citations.length}
        onCitation={(number) => onOpenSource(result.citations[number - 1])}
        className="text-body-lg"
      />
      <div className="mt-4">
        <h3 className="text-caption font-medium uppercase tracking-wide text-muted-foreground">Sources</h3>
        <ul className="mt-2 flex flex-wrap gap-2">
          {result.citations.map((citation, index) => (
            <li key={`${citation.chunk_id}-${index}`} className="max-w-full">
              <CitationChip source={citation} number={index + 1} onOpen={() => onOpenSource(citation)} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function Thinking() {
  return (
    <div role="status" aria-label="Reading your materials" className="space-y-2.5">
      <p className="text-body text-muted-foreground">Reading your materials</p>
      <div className="h-3 w-11/12 animate-pulse rounded-full bg-muted" />
      <div className="h-3 w-4/5 animate-pulse rounded-full bg-muted" />
      <div className="h-3 w-2/3 animate-pulse rounded-full bg-muted" />
    </div>
  )
}

interface AskAnswerProps {
  exchange: Exchange
  courseId: string
  onRetry: () => void
  onOpenSource: (citation: Citation) => void
}

export function AskAnswer({ exchange, courseId, onRetry, onOpenSource }: AskAnswerProps) {
  return (
    <article aria-label={`Answer to: ${exchange.question}`} className="scroll-mt-6 space-y-4">
      <div className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-line rounded-card rounded-br-sm bg-brand-soft px-4 py-2.5 text-body-lg text-foreground">{exchange.question}</p>
      </div>
      {exchange.status === 'pending' && <Thinking />}
      {exchange.status === 'failed' && (
        <Alert variant="error" className="flex items-center justify-between gap-3">
          <span>{exchange.error}</span>
          <Button variant="outline" size="sm" onClick={onRetry} className="shrink-0">
            <RotateCcw className="h-4 w-4" />
            Try again
          </Button>
        </Alert>
      )}
      {exchange.status === 'answered' &&
        (exchange.result.citations.length === 0 ? (
          <NotCovered answer={exchange.result.answer} courseId={courseId} />
        ) : (
          <GroundedAnswer result={exchange.result} onOpenSource={onOpenSource} />
        ))}
    </article>
  )
}

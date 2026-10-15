import { ArrowUp, MessageCircleQuestion } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Textarea } from '@/components/ui/textarea'

export function AskView({ courseName }: { courseName: string }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <EmptyState
          icon={MessageCircleQuestion}
          title={`Ask ${courseName}`}
          description="Ask about anything in this course, like a slide you did not follow. Answers will use your professor's own terms and cite the slide or page they come from."
        >
          <Badge variant="brand">Arrives in the next update</Badge>
        </EmptyState>
      </div>
      <form
        className="shrink-0 border-t border-border bg-surface px-gutter py-4"
        aria-label="Ask a question"
      >
        <div className="mx-auto flex w-full max-w-prose items-end gap-2">
          <Textarea
            placeholder="e.g. I do not get slide 14"
            aria-label="Your question"
            rows={1}
            disabled
            className="min-h-[44px] resize-none"
          />
          <Button type="submit" size="icon" aria-label="Ask" disabled className="h-11 w-11 shrink-0">
            <ArrowUp className="h-5 w-5" />
          </Button>
        </div>
      </form>
    </div>
  )
}

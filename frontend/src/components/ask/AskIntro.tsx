import { MessageCircleQuestion } from 'lucide-react'
import { EmptyState } from '@/components/ui/empty-state'

interface AskIntroProps {
  courseName: string
  suggestions: string[]
  onSuggestion: (question: string) => void
}

export function AskIntro({ courseName, suggestions, onSuggestion }: AskIntroProps) {
  return (
    <EmptyState
      icon={MessageCircleQuestion}
      title={`Ask ${courseName}`}
      description="Ask about anything in this course, like a slide you did not follow. Answers use your professor’s own terms and cite the page they come from."
    >
      {suggestions.length > 0 && (
        <ul aria-label="Suggested questions" className="flex w-full flex-col gap-2">
          {suggestions.map((suggestion) => (
            <li key={suggestion}>
              <button
                type="button"
                onClick={() => onSuggestion(suggestion)}
                className="w-full rounded-card border border-border bg-surface px-4 py-3 text-left text-body text-foreground transition-colors hover:border-brand hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {suggestion}
              </button>
            </li>
          ))}
        </ul>
      )}
    </EmptyState>
  )
}

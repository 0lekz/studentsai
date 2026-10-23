'use client'

import { useLayoutEffect, useRef } from 'react'
import { ArrowUp, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

const MAX_HEIGHT_PX = 160

interface AskComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  busy: boolean
}

export function AskComposer({ value, onChange, onSubmit, busy }: AskComposerProps) {
  const textarea = useRef<HTMLTextAreaElement>(null)

  useLayoutEffect(() => {
    const element = textarea.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, MAX_HEIGHT_PX)}px`
  }, [value])

  const canSend = value.trim().length > 0 && !busy

  return (
    <form
      aria-label="Ask a question"
      className="shrink-0 border-t border-border bg-surface px-gutter pb-[max(1rem,env(safe-area-inset-bottom))] pt-4 md:pb-4"
      onSubmit={(event) => {
        event.preventDefault()
        if (canSend) onSubmit()
      }}
    >
      <div className="mx-auto flex w-full max-w-prose items-end gap-2">
        <Textarea
          ref={textarea}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              if (canSend) onSubmit()
            }
          }}
          placeholder="Ask about anything in this course"
          aria-label="Your question"
          rows={1}
          className="min-h-11 resize-none py-2.5 text-body-lg"
        />
        <Button type="submit" size="icon" aria-label="Ask" disabled={!canSend} className="h-11 w-11 shrink-0">
          {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <ArrowUp className="h-5 w-5" />}
        </Button>
      </div>
    </form>
  )
}

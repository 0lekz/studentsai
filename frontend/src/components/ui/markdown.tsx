'use client'

import { useMemo } from 'react'
import MarkdownIt from 'markdown-it'
import { cn } from '@/lib/utils'

interface RenderEnv {
  citationCount: number
}

const CITATION_MARKER = /^\[(\d{1,2})\](?!\()/

const markdown = new MarkdownIt({ html: false, linkify: true, breaks: false })

markdown.inline.ruler.before('link', 'citation', (state, silent) => {
  if (state.src.charCodeAt(state.pos) !== 0x5b) return false
  const match = CITATION_MARKER.exec(state.src.slice(state.pos))
  if (!match) return false
  if (!silent) state.push('citation', '', 0).meta = { number: Number(match[1]) }
  state.pos += match[0].length
  return true
})

markdown.renderer.rules.citation = (tokens, index, _options, env: RenderEnv) => {
  const number = tokens[index].meta.number as number
  if (number < 1 || number > env.citationCount) return `[${number}]`
  return `<button type="button" class="citation-marker" data-citation="${number}" aria-label="Open source ${number}">${number}</button>`
}

const renderLinkOpen = markdown.renderer.rules.link_open ?? ((tokens, index, options, _env, self) => self.renderToken(tokens, index, options))
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
  tokens[index].attrSet('target', '_blank')
  tokens[index].attrSet('rel', 'noopener noreferrer')
  return renderLinkOpen(tokens, index, options, env, self)
}

interface MarkdownProps {
  source: string
  citationCount?: number
  onCitation?: (number: number) => void
  className?: string
}

// Renders untrusted model output: raw HTML is disabled, so only markdown syntax produces markup.
export function Markdown({ source, citationCount = 0, onCitation, className }: MarkdownProps) {
  const html = useMemo(() => markdown.render(source, { citationCount } satisfies RenderEnv), [source, citationCount])

  return (
    <div
      className={cn('prose prose-app max-w-none', className)}
      onClick={(event) => {
        const marker = (event.target as HTMLElement).closest<HTMLElement>('[data-citation]')
        if (marker && onCitation) onCitation(Number(marker.dataset.citation))
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

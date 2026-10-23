'use client'

import Link from 'next/link'
import { Github } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/theme/ThemeToggle'
import { REPO_URL, UNDER_CONSTRUCTION } from '@/lib/launch'

const linkClass =
  'whitespace-nowrap rounded px-1 text-sm text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring'

export function PublicHeader() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-border bg-surface/80 backdrop-blur">
      <div className="flex w-full items-center justify-between px-6 py-3">
        <a
          href="#main"
          className="sr-only rounded bg-primary px-2 py-1 text-primary-foreground focus:not-sr-only focus:absolute focus:left-6 focus:top-3"
        >
          Skip to content
        </a>

        <Link href="/landing" className="flex items-center gap-2 rounded px-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary shadow-sm">
            <span className="text-sm font-bold text-primary-foreground">AI</span>
          </div>
          <span className="font-semibold text-foreground">StudentsAI</span>
        </Link>

        <nav className="flex items-center gap-2 sm:gap-3">
          <Link href="/auth" className={linkClass}>
            Log in
          </Link>
          {!UNDER_CONSTRUCTION && (
            <Button asChild className="h-8 px-3 sm:px-4">
              <Link href="/auth">Start free</Link>
            </Button>
          )}
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="StudentsAI on GitHub"
            className={`inline-flex items-center gap-1 ${linkClass}`}
          >
            <Github className="h-4 w-4" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
}

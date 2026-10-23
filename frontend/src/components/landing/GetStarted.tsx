import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { REPO_URL, UNDER_CONSTRUCTION } from '@/lib/launch'

export function GetStarted() {
  return (
    <div className="rounded-3xl border border-border bg-surface px-6 py-12 text-center shadow-sm md:px-14 md:py-16">
      <h2 className="text-4xl font-semibold text-foreground md:text-5xl">Bring one course</h2>
      <p className="mx-auto mt-5 max-w-2xl text-xl leading-relaxed text-muted-foreground">
        {UNDER_CONSTRUCTION
          ? 'The new version is being built in the open. Sign-up reopens with the relaunch, and existing accounts keep their notes.'
          : 'Add a course, drop in this week’s slides, and run your first session. StudentsAI is free while it is in early access.'}
      </p>
      {UNDER_CONSTRUCTION ? (
        <Button asChild size="lg" className="mt-8 h-12 px-8 text-body-lg">
          <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
            Follow the rebuild on GitHub
            <ArrowRight className="h-5 w-5" />
          </a>
        </Button>
      ) : (
        <Button asChild size="lg" className="mt-8 h-12 px-8 text-body-lg">
          <Link href="/auth">
            Start studying free
            <ArrowRight className="h-5 w-5" />
          </Link>
        </Button>
      )}
      <p className="mt-4 text-body text-muted-foreground">
        {UNDER_CONSTRUCTION ? 'Open source. No credit card, ever.' : 'No credit card required. Open source on GitHub.'}
      </p>
    </div>
  )
}

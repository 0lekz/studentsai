import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function GetStarted() {
  return (
    <div className="rounded-3xl border border-border bg-surface px-6 py-12 text-center shadow-sm md:px-14 md:py-16">
      <h2 className="text-4xl font-semibold text-foreground md:text-5xl">Bring one course</h2>
      <p className="mx-auto mt-5 max-w-2xl text-xl leading-relaxed text-muted-foreground">
        Add a course, drop in this week’s slides, and run your first session. StudentsAI is free while it is in early access.
      </p>
      <Button asChild size="lg" className="mt-8 h-12 px-8 text-body-lg">
        <Link href="/auth">
          Start studying free
          <ArrowRight className="h-5 w-5" />
        </Link>
      </Button>
      <p className="mt-4 text-body text-muted-foreground">No credit card required. Open source on GitHub.</p>
    </div>
  )
}

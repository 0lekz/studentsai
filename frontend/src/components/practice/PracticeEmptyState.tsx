import Link from 'next/link'
import { Layers, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'

export function PracticeEmptyState({ courseId }: { courseId: string }) {
  return (
    <EmptyState
      icon={Layers}
      title="Practice from your slides"
      description="One question at a time, with feedback that points to the slide or page the answer comes from. Questions are generated from this course's materials once that lands in the next update."
    >
      <Button size="lg" disabled className="w-full sm:w-auto">
        <Play className="h-4 w-4" />
        Start session
      </Button>
      <Button asChild variant="link" size="sm">
        <Link href={`/courses/${courseId}/materials`}>Open materials</Link>
      </Button>
    </EmptyState>
  )
}

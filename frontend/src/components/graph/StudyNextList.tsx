import Link from 'next/link'
import { Play } from 'lucide-react'
import type { ConceptMap } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { studyNext } from './conceptMapModel'
import { ConceptListItem } from './ConceptListItem'

interface StudyNextListProps {
  courseId: string
  map: ConceptMap
  selectedId: string | null
  onSelect: (conceptId: string) => void
}

function reason(prerequisites: Array<{ name: string }>): string {
  if (prerequisites.length === 0) return 'A starting point'
  return `You know ${prerequisites.map((prerequisite) => prerequisite.name).join(', ')}`
}

export function StudyNextList({ courseId, map, selectedId, onSelect }: StudyNextListProps) {
  const items = studyNext(map)

  return (
    <section aria-labelledby="study-next-title">
      <h2 id="study-next-title" className="text-body font-semibold text-foreground">
        Study this next
      </h2>
      <p className="mt-0.5 text-caption text-muted-foreground">Weak spots whose prerequisites you already know.</p>
      {items.length === 0 ? (
        <p className="mt-3 rounded-control bg-muted px-3 py-2.5 text-body text-muted-foreground">Every concept here is strong. Keep up with your daily reviews.</p>
      ) : (
        <>
          <ol className="-mx-3 mt-2">
            {items.map(({ node, prerequisites }) => (
              <li key={node.id}>
                <ConceptListItem
                  name={node.name}
                  mastery={node.mastery}
                  detail={reason(prerequisites)}
                  selected={node.id === selectedId}
                  onSelect={() => onSelect(node.id)}
                />
              </li>
            ))}
          </ol>
          <Button asChild className="mt-3 w-full">
            <Link href={`/courses/${courseId}/practice?concept=${items[0].node.id}`}>
              <Play className="h-4 w-4" />
              <span className="truncate">Practice {items[0].node.name}</span>
            </Link>
          </Button>
        </>
      )}
    </section>
  )
}

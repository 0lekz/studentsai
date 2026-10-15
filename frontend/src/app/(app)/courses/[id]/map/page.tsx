'use client'

import Link from 'next/link'
import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { NotebookPen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { NotesGraph } from '@/components/graph/NotesGraph'
import { useCourse } from '@/components/course/CourseProvider'

export default function MapPage() {
  const router = useRouter()
  const { course } = useCourse()
  const notesHref = `/courses/${course.id}/notes`

  const openNote = useCallback((noteId: string) => router.push(`${notesHref}?note=${noteId}`), [router, notesHref])

  return (
    <NotesGraph
      courseId={course.id}
      onNodeClick={openNote}
      emptyAction={
        <Button asChild>
          <Link href={notesHref}>
            <NotebookPen className="h-4 w-4" />
            Write a note
          </Link>
        </Button>
      }
    />
  )
}

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Archive, ArchiveRestore, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { api, type Course } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useSession } from '@/components/shell/SessionProvider'
import { CourseForm } from './CourseForm'

export function CourseActions({ course, onChanged }: { course: Course; onChanged: () => Promise<void> }) {
  const router = useRouter()
  const { toast } = useToast()
  const { reloadCourses } = useSession()
  const [editing, setEditing] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  const refresh = async () => {
    await Promise.all([onChanged(), reloadCourses()])
  }

  const toggleArchived = async () => {
    try {
      await api.updateCourse(course.id, { archived: !course.archived })
      await refresh()
    } catch (error) {
      toast({ title: 'Could not update the course', description: error instanceof Error ? error.message : undefined, variant: 'destructive' })
    }
  }

  const deleteCourse = async () => {
    try {
      await api.deleteCourse(course.id)
      await reloadCourses()
      router.replace('/today')
    } catch (error) {
      toast({ title: 'Could not delete the course', description: error instanceof Error ? error.message : undefined, variant: 'destructive' })
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label="Course options" className="text-muted-foreground hover:text-foreground">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuItem onClick={() => setEditing(true)}>
            <Pencil className="h-4 w-4" />
            Edit course
          </DropdownMenuItem>
          <DropdownMenuItem onClick={toggleArchived}>
            {course.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
            {course.archived ? 'Restore course' : 'Archive course'}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setConfirmingDelete(true)} className="text-destructive focus:text-destructive">
            <Trash2 className="h-4 w-4" />
            Delete course
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit course</DialogTitle>
            <DialogDescription>Name, term and exam date.</DialogDescription>
          </DialogHeader>
          <CourseForm
            initial={course}
            submitLabel="Save"
            onCancel={() => setEditing(false)}
            onSubmit={async (values) => {
              await api.updateCourse(course.id, values)
              await refresh()
              setEditing(false)
            }}
          />
        </DialogContent>
      </Dialog>

      <ConfirmationDialog
        isOpen={confirmingDelete}
        onClose={() => setConfirmingDelete(false)}
        onConfirm={deleteCourse}
        title="Delete course"
        description={`Delete "${course.name}" with its materials, notes and flashcards? This cannot be undone.`}
        confirmText="Delete course"
        variant="destructive"
      />
    </>
  )
}

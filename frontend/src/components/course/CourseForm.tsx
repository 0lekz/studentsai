'use client'

import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import type { Course, CourseCreate } from '@/lib/api'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/form-label'

const NAME_MAX_LENGTH = 120
const TERM_MAX_LENGTH = 60

interface CourseFormProps {
  initial?: Pick<Course, 'name' | 'term' | 'exam_date'>
  submitLabel: string
  onSubmit: (values: CourseCreate) => Promise<void>
  onCancel?: () => void
}

export function CourseForm({ initial, submitLabel, onSubmit, onCancel }: CourseFormProps) {
  const [name, setName] = useState(initial?.name ?? '')
  const [term, setTerm] = useState(initial?.term ?? '')
  const [examDate, setExamDate] = useState(initial?.exam_date ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) {
      setError('Give the course a name.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSubmit({ name: trimmedName, term: term.trim() || null, exam_date: examDate || null })
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not save the course.')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div className="space-y-2">
        <Label htmlFor="course-name">Name</Label>
        <Input
          id="course-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="e.g. Organic Chemistry"
          maxLength={NAME_MAX_LENGTH}
          autoFocus
          required
        />
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="course-term">
            Term <span className="font-normal text-muted-foreground">(optional)</span>
          </Label>
          <Input id="course-term" value={term} onChange={(event) => setTerm(event.target.value)} placeholder="e.g. Fall 2026" maxLength={TERM_MAX_LENGTH} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="course-exam">
            Exam date <span className="font-normal text-muted-foreground">(optional)</span>
          </Label>
          <Input id="course-exam" type="date" value={examDate} onChange={(event) => setExamDate(event.target.value)} />
        </div>
      </div>
      {error && <Alert variant="error">{error}</Alert>}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={saving || !name.trim()}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

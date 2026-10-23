'use client'

import { useState } from 'react'
import { Upload } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface UploadDropzoneProps {
  onFiles: (files: File[]) => void
  onBrowse: () => void
}

export function UploadDropzone({ onFiles, onBrowse }: UploadDropzoneProps) {
  const [dragging, setDragging] = useState(false)

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        onFiles(Array.from(event.dataTransfer.files))
      }}
      className={cn(
        'flex flex-col items-center rounded-card border-2 border-dashed px-6 py-12 text-center transition-colors',
        dragging ? 'border-brand bg-brand-soft' : 'border-border bg-surface'
      )}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-card bg-brand-soft text-brand-soft-foreground">
        <Upload className="h-6 w-6" aria-hidden />
      </div>
      <h2 className="text-title font-semibold text-foreground">Bring the course in</h2>
      <p className="mt-2 max-w-sm text-body text-muted-foreground">
        Drop lecture slides and PDFs here. Each file is split into sections with page references, ready for practice and questions.
      </p>
      <Button className="mt-6" onClick={onBrowse}>
        <Upload className="h-4 w-4" />
        Add files
      </Button>
      <p className="mt-3 text-caption text-muted-foreground">PDF, up to 25 MB each</p>
    </div>
  )
}

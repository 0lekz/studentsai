'use client'

import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import type { DocumentSummary } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { useToast } from '@/hooks/use-toast'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { Spinner } from '@/components/ui/spinner'
import { SectionToolbar } from '@/components/course/SectionToolbar'
import { ConceptExtractionCard } from './ConceptExtractionCard'
import { DocumentList } from './DocumentList'
import { UploadDropzone } from './UploadDropzone'
import { useCourseDocuments } from './useCourseDocuments'

export function MaterialsView({ courseId }: { courseId: string }) {
  const { toast } = useToast()
  const fileInput = useRef<HTMLInputElement>(null)
  const { documents, loadError, uploadingNames, uploadFailures, dismissFailures, upload, remove } = useCourseDocuments(courseId)
  const [pendingDelete, setPendingDelete] = useState<DocumentSummary | null>(null)

  const browse = () => fileInput.current?.click()
  const hasMaterials = (documents?.length ?? 0) > 0 || uploadingNames.length > 0

  const confirmDelete = async () => {
    if (!pendingDelete) return
    try {
      await remove(pendingDelete.id)
    } catch (error) {
      toast({ title: 'Could not delete the file', description: error instanceof Error ? error.message : undefined, variant: 'destructive' })
    }
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-content px-gutter py-section">
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          data-testid="materials-file-input"
          onChange={(event) => {
            upload(Array.from(event.target.files ?? []))
            event.target.value = ''
          }}
        />

        {hasMaterials && (
          <SectionToolbar
            title="Materials"
            description={documents ? pluralize(documents.length, 'file') : undefined}
            action={
              <Button onClick={browse}>
                <Upload className="h-4 w-4" />
                Add files
              </Button>
            }
          />
        )}

        {uploadFailures.length > 0 && (
          <Alert variant="error" className="mb-4 flex items-start justify-between gap-4">
            <ul className="space-y-1">
              {uploadFailures.map((failure) => (
                <li key={failure.filename}>
                  <span className="font-medium">{failure.filename}</span>: {failure.message}
                </li>
              ))}
            </ul>
            <button type="button" onClick={dismissFailures} className="shrink-0 text-caption font-medium underline">
              Dismiss
            </button>
          </Alert>
        )}

        {loadError && <Alert variant="error">{loadError}</Alert>}
        {!loadError && documents === null && <Spinner label="Loading materials" />}
        {documents !== null &&
          (hasMaterials ? (
            <>
              {documents.length > 0 && <ConceptExtractionCard courseId={courseId} documents={documents} />}
              <DocumentList documents={documents} uploadingNames={uploadingNames} onDelete={setPendingDelete} />
            </>
          ) : (
            <UploadDropzone onFiles={upload} onBrowse={browse} />
          ))}
      </div>

      <ConfirmationDialog
        isOpen={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        title="Delete file"
        description={pendingDelete ? `Delete "${pendingDelete.filename}" and its extracted sections?` : ''}
        confirmText="Delete"
        variant="destructive"
      />
    </div>
  )
}

'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, APIError, type DocumentSummary } from '@/lib/api'

export interface UploadFailure {
  filename: string
  message: string
}

interface PendingUpload {
  name: string
  knownIds: Set<string>
}

export function useCourseDocuments(courseId: string) {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([])
  const [uploadFailures, setUploadFailures] = useState<UploadFailure[]>([])
  const documentsRef = useRef(documents)

  useEffect(() => {
    documentsRef.current = documents
  }, [documents])

  // A list reload can land while an upload is still in flight; once the new file is listed, its upload row is redundant.
  const uploadingNames = useMemo(
    () =>
      pendingUploads
        .filter(({ name, knownIds }) => !(documents ?? []).some((document) => document.filename === name && !knownIds.has(document.id)))
        .map(({ name }) => name),
    [pendingUploads, documents]
  )

  const reload = useCallback(async () => {
    try {
      setDocuments(await api.getDocuments(courseId))
      setLoadError(null)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Could not load materials')
    }
  }, [courseId])

  useEffect(() => {
    setDocuments(null)
    reload()
  }, [reload])

  const upload = useCallback(async (files: File[]) => {
    if (files.length === 0) return
    setUploadFailures([])
    const knownIds = new Set((documentsRef.current ?? []).map((document) => document.id))
    setPendingUploads(files.map((file) => ({ name: file.name, knownIds })))
    const failures: UploadFailure[] = []
    for (const file of files) {
      try {
        const uploaded = await api.uploadDocument(courseId, file)
        setDocuments((current) => [uploaded, ...(current ?? []).filter((doc) => doc.id !== uploaded.id)])
      } catch (error) {
        failures.push({ filename: file.name, message: error instanceof APIError ? error.message : 'Upload failed' })
      } finally {
        setPendingUploads((pending) => pending.filter((upload) => upload.name !== file.name))
      }
    }
    setUploadFailures(failures)
  }, [courseId])

  const remove = useCallback(async (documentId: string) => {
    await api.deleteDocument(documentId)
    setDocuments((current) => (current ?? []).filter((doc) => doc.id !== documentId))
  }, [])

  return {
    documents,
    loadError,
    uploadingNames,
    uploadFailures,
    dismissFailures: () => setUploadFailures([]),
    reload,
    upload,
    remove,
  }
}

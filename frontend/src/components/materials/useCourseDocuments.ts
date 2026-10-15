'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, APIError, type DocumentSummary } from '@/lib/api'

export interface UploadFailure {
  filename: string
  message: string
}

export function useCourseDocuments(courseId: string) {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [uploadingNames, setUploadingNames] = useState<string[]>([])
  const [uploadFailures, setUploadFailures] = useState<UploadFailure[]>([])

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
    setUploadingNames(files.map((file) => file.name))
    const failures: UploadFailure[] = []
    for (const file of files) {
      try {
        const uploaded = await api.uploadDocument(courseId, file)
        setDocuments((current) => [uploaded, ...(current ?? []).filter((doc) => doc.id !== uploaded.id)])
      } catch (error) {
        failures.push({ filename: file.name, message: error instanceof APIError ? error.message : 'Upload failed' })
      } finally {
        setUploadingNames((names) => names.filter((name) => name !== file.name))
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

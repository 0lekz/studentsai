'use client'

import { useEffect, useState } from 'react'
import { api, type DocumentChunk } from '@/lib/api'

const chunksByDocument = new Map<string, Promise<DocumentChunk[]>>()

function chunksOf(documentId: string): Promise<DocumentChunk[]> {
  let pending = chunksByDocument.get(documentId)
  if (!pending) {
    pending = api.getDocumentChunks(documentId)
    pending.catch(() => chunksByDocument.delete(documentId))
    chunksByDocument.set(documentId, pending)
  }
  return pending
}

type ChunkState = { status: 'loading' } | { status: 'ready'; chunk: DocumentChunk | null } | { status: 'error'; message: string }

export function useSourceChunk(documentId: string | undefined, chunkId: string | undefined): ChunkState {
  const [state, setState] = useState<ChunkState>({ status: 'loading' })

  useEffect(() => {
    if (!documentId || !chunkId) return
    let cancelled = false
    setState({ status: 'loading' })
    chunksOf(documentId)
      .then((chunks) => !cancelled && setState({ status: 'ready', chunk: chunks.find((chunk) => chunk.id === chunkId) ?? null }))
      .catch((error) => !cancelled && setState({ status: 'error', message: error instanceof Error ? error.message : 'Could not load the source' }))
    return () => {
      cancelled = true
    }
  }, [documentId, chunkId])

  return state
}

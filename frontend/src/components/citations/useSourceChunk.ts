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

type ChunkState = { status: 'loading' } | { status: 'ready'; chunk: DocumentChunk } | { status: 'error'; message: string }

export function useSourceChunk(documentId: string | undefined, chunkId: string | undefined): ChunkState {
  const [state, setState] = useState<ChunkState>({ status: 'loading' })

  useEffect(() => {
    if (!documentId || !chunkId) return
    let cancelled = false
    setState({ status: 'loading' })
    chunksOf(documentId)
      .then((chunks) => {
        if (cancelled) return
        const chunk = chunks.find((candidate) => candidate.id === chunkId)
        setState(chunk ? { status: 'ready', chunk } : { status: 'error', message: 'This section could not be found.' })
      })
      .catch((error) => !cancelled && setState({ status: 'error', message: error instanceof Error ? error.message : 'Could not load the source' }))
    return () => {
      cancelled = true
    }
  }, [documentId, chunkId])

  return state
}

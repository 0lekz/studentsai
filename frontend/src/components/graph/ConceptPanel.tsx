'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Loader2, Pencil, Play, Trash2 } from 'lucide-react'
import { api, type DocumentSummary, type Citation, type Concept, type ConceptMap, type ConceptMapNode } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { Input } from '@/components/ui/input'
import { Sheet } from '@/components/ui/sheet'
import { MASTERY_LEVELS, formatMastery, masteryFillClass, masteryLevel } from '@/components/concepts/mastery'
import { CitationChip } from '@/components/citations/CitationChip'
import { dependentsOf, prerequisitesOf, relatedTo } from './conceptMapModel'

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h3 className="text-caption font-medium uppercase tracking-wide text-muted-foreground">{children}</h3>
}

function ConceptLinks({ label, nodes, onSelect }: { label: string; nodes: ConceptMapNode[]; onSelect: (id: string) => void }) {
  if (nodes.length === 0) return null
  return (
    <section>
      <SectionLabel>{label}</SectionLabel>
      <ul className="mt-2 flex flex-wrap gap-2">
        {nodes.map((node) => (
          <li key={node.id}>
            <button
              type="button"
              onClick={() => onSelect(node.id)}
              className="inline-flex h-9 items-center gap-2 rounded-full border border-border bg-surface px-3 text-body text-foreground transition-colors hover:border-brand hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span aria-hidden className={cn('h-2.5 w-2.5 rounded-full', masteryFillClass[masteryLevel(node.mastery)])} />
              {node.name}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

function RenameForm({ initial, onCancel, onSave }: { initial: string; onCancel: () => void; onSave: (name: string) => Promise<void> }) {
  const [name, setName] = useState(initial)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  return (
    <form
      className="space-y-3"
      onSubmit={async (event) => {
        event.preventDefault()
        if (!name.trim() || name.trim() === initial) return onCancel()
        setSaving(true)
        setError(null)
        try {
          await onSave(name.trim())
        } catch (saveError) {
          setError(saveError instanceof Error ? saveError.message : 'Could not rename the concept')
          setSaving(false)
        }
      }}
    >
      <Input value={name} onChange={(event) => setName(event.target.value)} aria-label="Concept name" maxLength={120} autoFocus />
      {error && <Alert variant="error">{error}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || !name.trim()}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          Save
        </Button>
      </div>
    </form>
  )
}

interface ConceptPanelProps {
  courseId: string
  map: ConceptMap
  node: ConceptMapNode | null
  concept: Concept | undefined
  documents: DocumentSummary[]
  onClose: () => void
  onSelect: (conceptId: string) => void
  onOpenSource: (citation: Citation) => void
  onChanged: () => Promise<void>
}

export function ConceptPanel({ courseId, map, node, concept, documents, onClose, onSelect, onOpenSource, onChanged }: ConceptPanelProps) {
  const { toast } = useToast()
  const [renaming, setRenaming] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [lastNode, setLastNode] = useState(node)
  if (node && node !== lastNode) {
    setLastNode(node)
    setRenaming(false)
  }
  const shown = node ?? lastNode
  const filenames = new Map(documents.map((document) => [document.id, document.filename]))
  const level = shown ? MASTERY_LEVELS.find((entry) => entry.level === masteryLevel(shown.mastery)) : undefined

  return (
    <>
      <Sheet
        open={node !== null}
        onOpenChange={(open) => !open && onClose()}
        title={shown?.name}
        description={shown ? `${level?.label} · ${pluralize(shown.question_count, 'question')}` : undefined}
      >
        {shown && (
          <div className="space-y-6">
            {renaming ? (
              <RenameForm
                initial={shown.name}
                onCancel={() => setRenaming(false)}
                onSave={async (name) => {
                  await api.renameConcept(courseId, shown.id, name)
                  await onChanged()
                  setRenaming(false)
                }}
              />
            ) : (
              <div className="flex items-center gap-3 rounded-card bg-muted px-4 py-3">
                <span aria-hidden className={cn('h-4 w-4 shrink-0 rounded-full', masteryFillClass[masteryLevel(shown.mastery)])} />
                <p className="min-w-0 flex-1 text-body text-foreground">
                  <span className="font-semibold">{formatMastery(shown.mastery)}</span>
                  {shown.mastery !== null && <span className="text-muted-foreground"> mastery</span>}
                </p>
              </div>
            )}

            {concept?.description && <p className="text-body-lg text-foreground">{concept.description}</p>}

            <ConceptLinks label="Builds on" nodes={prerequisitesOf(map, shown.id)} onSelect={onSelect} />
            <ConceptLinks label="Leads to" nodes={dependentsOf(map, shown.id)} onSelect={onSelect} />
            <ConceptLinks label="Related" nodes={relatedTo(map, shown.id)} onSelect={onSelect} />

            {concept && concept.sources.length > 0 && (
              <section>
                <SectionLabel>Where it appears</SectionLabel>
                <ul className="mt-2 flex flex-col items-start gap-2">
                  {concept.sources.map((source) => {
                    const citation: Citation = { ...source, filename: filenames.get(source.document_id) ?? '', excerpt: '' }
                    return (
                      <li key={source.chunk_id} className="max-w-full">
                        <CitationChip source={citation} onOpen={() => onOpenSource(citation)} />
                      </li>
                    )
                  })}
                </ul>
              </section>
            )}

            <div className="space-y-2 border-t border-border pt-5">
              <Button asChild size="lg" className="w-full">
                <Link href={`/courses/${courseId}/practice?concept=${shown.id}`}>
                  <Play className="h-4 w-4" />
                  Practice this concept
                </Link>
              </Button>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" onClick={() => setRenaming(true)} disabled={renaming}>
                  <Pencil className="h-4 w-4" />
                  Rename
                </Button>
                <Button variant="outline" onClick={() => setConfirmingDelete(true)} className="text-destructive hover:text-destructive">
                  <Trash2 className="h-4 w-4" />
                  Delete
                </Button>
              </div>
            </div>
          </div>
        )}
      </Sheet>

      <ConfirmationDialog
        isOpen={confirmingDelete}
        onClose={() => setConfirmingDelete(false)}
        onConfirm={async () => {
          if (!shown) return
          try {
            await api.deleteConcept(courseId, shown.id)
            onClose()
            await onChanged()
          } catch (error) {
            toast({ title: 'Could not delete the concept', description: error instanceof Error ? error.message : undefined, variant: 'destructive' })
          }
        }}
        title="Delete concept"
        description={shown ? `Remove "${shown.name}" from the map? Its questions stay in your practice pool.` : ''}
        confirmText="Delete concept"
        variant="destructive"
      />
    </>
  )
}

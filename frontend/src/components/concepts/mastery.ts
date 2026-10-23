export type MasteryLevel = 'none' | 'low' | 'mid' | 'high'

export const STRONG_MASTERY = 0.75
const GROWING_MASTERY = 0.4

export const MASTERY_LEVELS: ReadonlyArray<{ level: MasteryLevel; label: string; range?: string }> = [
  { level: 'none', label: 'No questions yet' },
  { level: 'low', label: 'Just started', range: '0-39%' },
  { level: 'mid', label: 'Getting there', range: '40-74%' },
  { level: 'high', label: 'Strong', range: '75-100%' },
]

export function masteryLevel(mastery: number | null): MasteryLevel {
  if (mastery === null) return 'none'
  if (mastery >= STRONG_MASTERY) return 'high'
  if (mastery >= GROWING_MASTERY) return 'mid'
  return 'low'
}

export function formatMastery(mastery: number | null): string {
  return mastery === null ? 'No questions yet' : `${Math.round(mastery * 100)}%`
}

export const masteryFillClass: Record<MasteryLevel, string> = {
  none: 'bg-surface border border-dashed border-muted-foreground',
  low: 'bg-mastery-low',
  mid: 'bg-mastery-mid',
  high: 'bg-mastery-high',
}

export const masteryFillVar: Record<MasteryLevel, string> = {
  none: 'hsl(var(--surface))',
  low: 'hsl(var(--mastery-low))',
  mid: 'hsl(var(--mastery-mid))',
  high: 'hsl(var(--mastery-high))',
}

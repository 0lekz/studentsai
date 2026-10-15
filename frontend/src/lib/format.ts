const DAY_MS = 24 * 60 * 60 * 1000

function startOfLocalDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
}

export function parseDateOnly(value: string): Date {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function daysUntil(dateOnly: string, now: Date = new Date()): number {
  return Math.round((startOfLocalDay(parseDateOnly(dateOnly)) - startOfLocalDay(now)) / DAY_MS)
}

export function formatExamCountdown(dateOnly: string, now: Date = new Date()): string {
  const days = daysUntil(dateOnly, now)
  if (days === 0) return 'Exam today'
  if (days === 1) return 'Exam tomorrow'
  if (days > 1) return `Exam in ${days} days`
  if (days === -1) return 'Exam was yesterday'
  return `Exam was ${-days} days ago`
}

export function formatShortDate(value: string): string {
  const date = value.length === 10 ? parseDateOnly(value) : new Date(value)
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function pluralize(count: number, singular: string, plural: string = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`
}

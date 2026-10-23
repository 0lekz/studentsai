import { cn } from '@/lib/utils'

export function BrandMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-brand text-caption font-bold text-white shadow-sm', className)}
    >
      AI
    </span>
  )
}

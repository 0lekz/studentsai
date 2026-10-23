import * as React from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: React.ReactNode
  children?: React.ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, description, children, className }: EmptyStateProps) {
  return (
    <div className={cn('mx-auto flex max-w-md flex-col items-center px-gutter py-12 text-center', className)}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-card bg-brand-soft text-brand-soft-foreground">
        <Icon className="h-6 w-6" aria-hidden />
      </div>
      <h2 className="text-title font-semibold text-foreground">{title}</h2>
      <p className="mt-2 text-body text-muted-foreground">{description}</p>
      {children && <div className="mt-6 flex w-full flex-col items-center gap-3">{children}</div>}
    </div>
  )
}

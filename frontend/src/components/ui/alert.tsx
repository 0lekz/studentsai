import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const alertVariants = cva('rounded-control border px-4 py-3 text-body', {
  variants: {
    variant: {
      info: 'border-border bg-muted text-foreground',
      success: 'border-transparent bg-success-soft text-success-soft-foreground',
      warning: 'border-transparent bg-warning-soft text-warning-soft-foreground',
      error: 'border-transparent bg-destructive-soft text-destructive-soft-foreground',
    },
  },
  defaultVariants: { variant: 'info' },
})

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {}

export function Alert({ className, variant, ...props }: AlertProps) {
  return <div role={variant === 'error' ? 'alert' : 'status'} className={cn(alertVariants({ variant }), className)} {...props} />
}

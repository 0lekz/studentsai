interface SectionToolbarProps {
  title: string
  description?: React.ReactNode
  action?: React.ReactNode
}

export function SectionToolbar({ title, description, action }: SectionToolbarProps) {
  return (
    <div className="mb-6 flex items-center justify-between gap-4">
      <div className="min-w-0">
        <h2 className="text-title font-semibold text-foreground">{title}</h2>
        {description && <p className="text-body text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

interface SettingsSectionProps {
  id: string
  title: string
  description: string
  children: React.ReactNode
}

export function SettingsSection({ id, title, description, children }: SettingsSectionProps) {
  return (
    <section aria-labelledby={`${id}-title`} className="grid gap-4 border-t border-border py-section first-of-type:border-t-0 first-of-type:pt-0 lg:grid-cols-[14rem_1fr] lg:gap-8">
      <div>
        <h2 id={`${id}-title`} className="text-title font-semibold text-foreground">{title}</h2>
        <p className="mt-1 text-body text-muted-foreground">{description}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}

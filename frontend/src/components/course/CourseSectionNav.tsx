import Link from 'next/link'
import { cn } from '@/lib/utils'
import { COURSE_SECTIONS, type CourseSectionSlug } from './sections'

interface CourseSectionNavProps {
  courseId: string
  active?: CourseSectionSlug
}

export function CourseSectionTabs({ courseId, active }: CourseSectionNavProps) {
  return (
    <nav aria-label="Course sections" className="-mb-px flex gap-6">
      {COURSE_SECTIONS.map(({ slug, label }) => (
        <Link
          key={slug}
          href={`/courses/${courseId}/${slug}`}
          aria-current={active === slug ? 'page' : undefined}
          className={cn(
            'border-b-2 py-3 text-body font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            active === slug ? 'border-brand text-foreground' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'
          )}
        >
          {label}
        </Link>
      ))}
    </nav>
  )
}

export function CourseSectionBar({ courseId, active }: CourseSectionNavProps) {
  return (
    <nav
      aria-label="Course sections"
      className="grid shrink-0 grid-cols-5 border-t border-border bg-surface pb-[env(safe-area-inset-bottom)]"
    >
      {COURSE_SECTIONS.map(({ slug, label, icon: Icon }) => (
        <Link
          key={slug}
          href={`/courses/${courseId}/${slug}`}
          aria-current={active === slug ? 'page' : undefined}
          className={cn(
            'flex h-bottombar flex-col items-center justify-center gap-1 text-caption font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
            active === slug ? 'text-brand-soft-foreground' : 'text-muted-foreground'
          )}
        >
          <Icon className="h-5 w-5" aria-hidden />
          {label}
        </Link>
      ))}
    </nav>
  )
}

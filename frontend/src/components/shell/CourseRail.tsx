'use client'

import Link from 'next/link'
import { LogOut, Plus, Settings, Sun } from 'lucide-react'
import type { CourseListItem, User } from '@/lib/api'
import { formatExamCountdown } from '@/lib/format'
import { cn } from '@/lib/utils'
import { ThemeToggle } from '@/components/theme/ThemeToggle'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { BrandMark } from './BrandMark'
import { RailLink } from './RailLink'

interface CourseRailProps {
  user: User
  courses: CourseListItem[] | null
  coursesError: string | null
  pathname: string
  activeCourseId?: string
  onNavigate?: () => void
  onLogout: () => void
}

function courseSubtitle(course: CourseListItem): string | null {
  if (course.exam_date && !course.archived) return formatExamCountdown(course.exam_date)
  return course.term
}

function CourseItem({ course, active, onNavigate }: { course: CourseListItem; active: boolean; onNavigate?: () => void }) {
  const subtitle = courseSubtitle(course)
  return (
    <li>
      <Link
        href={`/courses/${course.id}/materials`}
        onClick={onNavigate}
        aria-current={active ? 'page' : undefined}
        className={cn(
          'flex flex-col rounded-control px-3 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          active ? 'bg-brand-soft' : 'hover:bg-accent'
        )}
      >
        <span className={cn('truncate text-body font-medium', active ? 'text-brand-soft-foreground' : 'text-foreground')}>
          {course.name}
        </span>
        {subtitle && <span className="truncate text-caption text-muted-foreground">{subtitle}</span>}
      </Link>
    </li>
  )
}

export function CourseRail({ user, courses, coursesError, pathname, activeCourseId, onNavigate, onLogout }: CourseRailProps) {
  const activeCourses = courses?.filter((course) => !course.archived) ?? []
  const archivedCourses = courses?.filter((course) => course.archived) ?? []

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-topbar shrink-0 items-center gap-2 px-5">
        <BrandMark />
        <span className="text-body-lg font-semibold text-foreground">StudentsAI</span>
      </div>

      <div className="px-3">
        <RailLink href="/today" icon={Sun} active={pathname === '/today'} onNavigate={onNavigate}>
          Today
        </RailLink>
      </div>

      <nav aria-label="Courses" className="mt-6 flex min-h-0 flex-1 flex-col">
        <h2 className="px-6 pb-2 text-caption font-medium uppercase tracking-wide text-muted-foreground">Courses</h2>
        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {coursesError && <p className="px-3 py-2 text-caption text-destructive">{coursesError}</p>}
          {courses && (
            <ul className="space-y-0.5">
              {activeCourses.map((course) => (
                <CourseItem key={course.id} course={course} active={course.id === activeCourseId} onNavigate={onNavigate} />
              ))}
            </ul>
          )}
          <Link
            href="/courses/new"
            onClick={onNavigate}
            aria-current={pathname === '/courses/new' ? 'page' : undefined}
            className={cn(
              'mt-1 flex h-9 items-center gap-3 rounded-control px-3 text-body font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              pathname === '/courses/new' ? 'bg-brand-soft text-brand-soft-foreground' : 'text-muted-foreground hover:bg-accent hover:text-foreground'
            )}
          >
            <Plus className="h-4 w-4" aria-hidden />
            Add course
          </Link>
          {archivedCourses.length > 0 && (
            <>
              <h3 className="px-3 pb-1 pt-5 text-caption font-medium uppercase tracking-wide text-muted-foreground">Archived</h3>
              <ul className="space-y-0.5 opacity-80">
                {archivedCourses.map((course) => (
                  <CourseItem key={course.id} course={course} active={course.id === activeCourseId} onNavigate={onNavigate} />
                ))}
              </ul>
            </>
          )}
        </div>
      </nav>

      <div className="shrink-0 space-y-1 border-t border-border p-3">
        <RailLink href="/settings" icon={Settings} active={pathname === '/settings'} onNavigate={onNavigate}>
          Settings
        </RailLink>
        <div className="flex items-center gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-11 min-w-0 flex-1 justify-start gap-3 px-3">
                <span aria-hidden className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-caption font-semibold uppercase text-foreground">
                  {user.username.slice(0, 1)}
                </span>
                <span className="min-w-0 text-left">
                  <span className="block truncate text-body font-medium text-foreground">{user.username}</span>
                  <span className="block truncate text-caption font-normal text-muted-foreground">{user.email}</span>
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" side="top" className="w-56">
              <DropdownMenuLabel className="truncate font-normal text-muted-foreground">{user.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onLogout} className="text-destructive focus:text-destructive">
                <LogOut className="h-4 w-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <ThemeToggle />
        </div>
      </div>
    </div>
  )
}

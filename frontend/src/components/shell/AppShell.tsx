'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ConstructionNotice } from '@/components/ui/construction-notice'
import { BrandMark } from './BrandMark'
import { CourseRail } from './CourseRail'
import { RailDrawer } from './RailDrawer'
import { useSession } from './SessionProvider'

function activeCourseIdFrom(pathname: string): string | undefined {
  const match = pathname.match(/^\/courses\/([^/]+)/)
  return match && match[1] !== 'new' ? match[1] : undefined
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { user, courses, coursesError, logout } = useSession()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const rail = (onNavigate?: () => void) => (
    <CourseRail
      user={user}
      courses={courses}
      coursesError={coursesError}
      pathname={pathname}
      activeCourseId={activeCourseIdFrom(pathname)}
      onNavigate={onNavigate}
      onLogout={logout}
    />
  )

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <aside className="hidden w-rail shrink-0 border-r border-border bg-surface md:block">{rail()}</aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-topbar shrink-0 items-center gap-2 border-b border-border bg-surface px-2 md:hidden">
          <Button variant="ghost" size="icon" aria-label="Open navigation" onClick={() => setDrawerOpen(true)}>
            <Menu className="h-5 w-5" />
          </Button>
          <BrandMark className="h-7 w-7" />
          <span className="text-body-lg font-semibold">StudentsAI</span>
        </header>
        <ConstructionNotice variant="strip" />
        <main className="flex min-h-0 flex-1 flex-col">{children}</main>
      </div>

      <RailDrawer open={drawerOpen} onOpenChange={setDrawerOpen}>
        {rail(() => setDrawerOpen(false))}
      </RailDrawer>
    </div>
  )
}

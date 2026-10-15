import { AppShell } from '@/components/shell/AppShell'
import { SessionProvider } from '@/components/shell/SessionProvider'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AppShell>{children}</AppShell>
    </SessionProvider>
  )
}

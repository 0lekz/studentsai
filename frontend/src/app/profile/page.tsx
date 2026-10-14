/**
 * Design rationale (Profile): Centered, low-chrome layout reminiscent of monkeytype.
 * Reuses shadcn Cards and Tailwind spacing; accents in #f97316 are used sparingly for focus.
 */
'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/Header'
import { ProfileHeader } from '@/components/profile/ProfileHeader'
import { StatsRow } from '@/components/profile/StatsRow'
import { Heatmap } from '@/components/profile/Heatmap'
import { ActivityList } from '@/components/profile/ActivityList'
import { api, type ActivityDayCount, type EventItem, type ProfileSummary } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function ProfilePage() {
  const [summary, setSummary] = useState<ProfileSummary | null>(null)
  const [events, setEvents] = useState<EventItem[]>([])
  const [heatmap, setHeatmap] = useState<ActivityDayCount[]>([])
  const [flashcardStats, setFlashcardStats] = useState({
    totalCards: 0,
    dueToday: 0,
    mastered: 0,
    learning: 0,
    averageScore: 0
  })
  const [user, setUser] = useState<{ id: string; email: string; username?: string } | null>(null)

  // Helper function to get current UTC date
  const getCurrentUTCDate = () => {
    const now = new Date()
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  }

  useEffect(() => {
    // Load user on client only to avoid hydration mismatch
    try {
      const raw = localStorage.getItem('user')
      setUser(raw ? JSON.parse(raw) : null)
    } catch {}

    const run = async () => {
      try {
        const s = await api.getProfileSummary()
        setSummary(s)
      } catch {}
      try {
        const recent = await api.getRecentEvents()
        setEvents(recent)
      } catch {}
      try {
        // last 180 days UTC continuous grid, even if no activity
        // Use UTC dates to align with backend storage
        const todayUTC = getCurrentUTCDate()
        const end = todayUTC
        const start = new Date(todayUTC)
        start.setUTCDate(todayUTC.getUTCDate() - 179)
        
        const fmt = (d: Date) => d.toISOString().slice(0, 10)
        const data = await api.getProfileActivity(fmt(start), fmt(end), 'all')
        // ensure continuity if backend returns gaps
        const map = new Map(data.days.map(d => [d.date, d]))
        const days: ActivityDayCount[] = []
        const cur = new Date(start)
        while (cur <= end) {
          const key = fmt(cur)
          days.push(map.get(key) || { date: key, count: 0 })
          cur.setUTCDate(cur.getUTCDate() + 1)
        }
        setHeatmap(days)
      } catch {}
      
      // Load flashcard stats
      try {
        const flashcards = await api.getUserFlashcards()
        const stats = {
          totalCards: flashcards.length,
          // FlashcardResponse carries no next-review date, so no card is ever counted as due
          dueToday: 0,
          mastered: flashcards.filter(f => (f.mastery_level || 0) >= 80).length,
          learning: flashcards.filter(f => (f.mastery_level || 0) < 80).length,
          averageScore: flashcards.reduce((sum, f) => sum + (f.last_performance || 0), 0) / Math.max(flashcards.length, 1)
        }
        setFlashcardStats(stats)
      } catch {}
    }
    run()
  }, [])

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-[#0f1115]">
      {/* Shared header, context=profile to show Notes/Settings */}
      {user ? (
        <Header
          user={{ id: user.id, email: user.email, username: user.username || '', created_at: '' }}
          onLogout={() => { localStorage.clear(); window.location.replace('/landing') }}
          context="profile"
        />
      ) : null}
      <section className="mx-auto max-w-6xl px-6 py-10">
        <ProfileHeader name={user?.username || 'Profile'} email={user?.email || 'you@example.com'} />
        {summary && (
          <div className="mb-6">
            <StatsRow
              notesCreated={summary.notes_created}
              notesReviewed={summary.notes_reviewed}
              flashcardsCreated={summary.flashcards_created}
              flashcardsReviewed={summary.flashcards_reviewed}
              activity7d={summary.activity_7d}
              activity30d={summary.activity_30d}
            />
          </div>
        )}
        
        {/* Flashcard Section */}
        <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="w-6 h-6">
                <img src="/icons/flashcards-icon.svg" alt="Flashcards" className="w-full h-full" />
              </div>
              Flashcards
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{flashcardStats.totalCards}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Total</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{flashcardStats.dueToday}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Due Today</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{flashcardStats.mastered}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Mastered</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{Math.round(flashcardStats.averageScore)}%</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Avg Score</div>
              </div>
            </div>
            <div className="text-center">
              <Button
                onClick={() => window.location.href = '/flashcards'}
                className="w-full bg-orange-600 hover:bg-orange-700 text-white border-0 shadow-sm"
              >
                Go to Flashcards
              </Button>
            </div>
          </CardContent>
        </Card>
        
        <div className="mt-8">
          <Heatmap days={heatmap} />
        </div>
        <div className="mt-8">
          <ActivityList events={events} />
        </div>
      </section>
    </main>
  )
}



/**
 * ActivityList: shows recent events with compact icons and UTC timestamps.
 */
'use client'

import type { JSX } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { EventItem, EventType } from '@/lib/api'
import { FilePlus, BookOpenCheck } from 'lucide-react'
import Image from 'next/image'

const iconFor: Record<EventType, JSX.Element> = {
  NOTE_CREATED: <FilePlus className="h-4 w-4 text-orange-500" />,
  NOTE_REVIEWED: <BookOpenCheck className="h-4 w-4 text-orange-500" />,
  FLASHCARD_CREATED: (
    <Image src="/icons/flashcards-icon.svg" alt="Flashcard created" width={16} height={16} className="opacity-90" />
  ),
  FLASHCARD_REVIEWED: (
    <Image src="/icons/flashcards-icon.svg" alt="Flashcard reviewed" width={16} height={16} className="opacity-90" />
  ),
}

interface ActivityListProps {
  events: EventItem[]
}

export function ActivityList({ events }: ActivityListProps) {
  return (
    <Card className="border border-gray-200 dark:border-[#232a36] bg-white dark:bg-[#141820]">
      <CardContent className="p-5">
        <h2 className="text-sm font-medium text-gray-900 dark:text-gray-200 mb-3">Recent activity</h2>
        {events.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <p>No recent events</p>
            <p className="text-xs mt-2">Create notes or review flashcards to see your activity here.</p>
          </div>
        ) : (
          <ul className="space-y-2">
            {events.map((e) => {
              const dt = new Date(e.occurred_at)
              const label = dt.toISOString().replace('T', ' ').replace('Z', ' UTC')
              return (
                <li key={e.id} className="flex items-center justify-between rounded border border-gray-200 dark:border-[#232a36] px-3 py-2 bg-gray-50 dark:bg-[#0f1115]">
                  <div className="flex items-center gap-2">
                    {iconFor[e.event_type]}
                    <span className="text-sm text-gray-900 dark:text-gray-200">{e.event_type.replaceAll('_', ' ')}</span>
                  </div>
                  <time className="text-xs text-gray-600 dark:text-gray-400">{label}</time>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}



/**
 * Design rationale: Minimal settings with clear labels and accessible controls.
 * Matches shadcn inputs/buttons; uses orange focus accents sparingly.
 */
'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface SettingsPanelProps {
  initialTheme?: 'light' | 'dark'
}

export function SettingsPanel({ initialTheme = 'light' }: SettingsPanelProps) {
  const [theme, setTheme] = useState<'light' | 'dark'>(initialTheme)
  const [summaryLen, setSummaryLen] = useState(3)
  const [difficulty, setDifficulty] = useState(2)
  const [isPublic, setIsPublic] = useState(false)

  return (
    <Card>
      <CardContent className="p-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium text-gray-800">Theme</label>
            <div className="mt-2 flex items-center gap-2">
              <Button
                type="button"
                variant={theme === 'light' ? 'default' : 'outline'}
                className={theme === 'light' ? 'bg-orange-500 hover:bg-orange-600' : ''}
                onClick={() => setTheme('light')}
                aria-pressed={theme === 'light'}
              >
                Light
              </Button>
              <Button
                type="button"
                variant={theme === 'dark' ? 'default' : 'outline'}
                className={theme === 'dark' ? 'bg-orange-500 hover:bg-orange-600' : ''}
                onClick={() => setTheme('dark')}
                aria-pressed={theme === 'dark'}
              >
                Dark
              </Button>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-800">Summary length</label>
            <input
              aria-label="Summary length"
              type="range"
              min={1}
              max={5}
              value={summaryLen}
              onChange={(e) => setSummaryLen(Number(e.target.value))}
              className="mt-2 w-full accent-orange-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-800">Flashcard difficulty</label>
            <input
              aria-label="Flashcard difficulty"
              type="range"
              min={1}
              max={5}
              value={difficulty}
              onChange={(e) => setDifficulty(Number(e.target.value))}
              className="mt-2 w-full accent-orange-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-800">Data export</label>
            <div className="mt-2 flex gap-2">
              <Button variant="outline">Export CSV</Button>
            </div>
          </div>

          <div className="sm:col-span-2">
            <label className="text-sm font-medium text-gray-800">Privacy</label>
            <div className="mt-2 flex items-center gap-2">
              <input
                id="privacy"
                type="checkbox"
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
              />
              <label htmlFor="privacy" className="text-sm text-gray-700">
                Make my notes public
              </label>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}



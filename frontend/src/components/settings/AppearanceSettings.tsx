'use client'

import { useEffect, useRef } from 'react'
import { Laptop, Moon, Sun } from 'lucide-react'
import { api, type SettingsAppearance } from '@/lib/api'
import { useThemeMode, type ThemeMode } from '@/lib/theme'
import { cn } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

const OPTIONS: ReadonlyArray<{ mode: ThemeMode; label: string; icon: typeof Sun }> = [
  { mode: 'light', label: 'Light', icon: Sun },
  { mode: 'dark', label: 'Dark', icon: Moon },
  { mode: 'system', label: 'System', icon: Laptop },
]

const DEFAULT_APPEARANCE: SettingsAppearance = { theme: 'system', font_size: 'medium', layout_density: 'comfortable' }

export function AppearanceSettings() {
  const { toast } = useToast()
  const { mode, setMode } = useThemeMode()
  const savedAppearance = useRef<SettingsAppearance>(DEFAULT_APPEARANCE)

  useEffect(() => {
    api.getAppearanceSettings()
      .then((settings) => {
        savedAppearance.current = settings
      })
      .catch((error) => console.error('Failed to load appearance settings:', error))
  }, [])

  const choose = async (next: ThemeMode) => {
    setMode(next)
    try {
      savedAppearance.current = await api.updateAppearanceSettings({ ...savedAppearance.current, theme: next })
    } catch {
      toast({ title: 'Could not save your theme', description: 'It applies on this device but did not sync to your account.', variant: 'destructive' })
    }
  }

  return (
    <div role="radiogroup" aria-label="Theme" className="grid max-w-md grid-cols-3 gap-2">
      {OPTIONS.map(({ mode: option, label, icon: Icon }) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={mode === option}
          onClick={() => choose(option)}
          className={cn(
            'flex h-20 flex-col items-center justify-center gap-2 rounded-card border text-body font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            mode === option ? 'border-brand bg-brand-soft text-brand-soft-foreground' : 'border-border bg-surface text-foreground hover:bg-accent'
          )}
        >
          <Icon className="h-5 w-5" aria-hidden />
          {label}
        </button>
      ))}
    </div>
  )
}

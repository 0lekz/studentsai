import { cn } from '@/lib/utils'
import { MAX_PASSWORD_SCORE, strengthLabel, type PasswordStrength } from './passwordStrength'

function tone(score: number): { bar: string; text: string } {
  if (score <= 2) return { bar: 'bg-destructive', text: 'text-destructive' }
  if (score <= 3) return { bar: 'bg-brand', text: 'text-brand-soft-foreground' }
  if (score <= 4) return { bar: 'bg-warning', text: 'text-warning-soft-foreground' }
  return { bar: 'bg-success', text: 'text-success' }
}

export function PasswordStrengthMeter({ strength }: { strength: PasswordStrength }) {
  const { bar, text } = tone(strength.score)
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <span className="text-caption text-muted-foreground">Strength</span>
        <span className={cn('text-caption font-medium', text)}>{strengthLabel(strength.score)}</span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
          <div className={cn('h-full transition-all duration-300', bar)} style={{ width: `${(strength.score / MAX_PASSWORD_SCORE) * 100}%` }} />
        </div>
      </div>
      {strength.feedback && <p className="text-caption text-muted-foreground">{strength.feedback}</p>}
    </div>
  )
}

import { CheckCircle, Loader2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/form-label'
import type { UsernameStatus } from './useUsernameAvailability'

interface UsernameFieldProps {
  value: string
  onChange: (value: string) => void
  status: UsernameStatus
}

export function UsernameField({ value, onChange, status }: UsernameFieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor="username">Username</Label>
      <div className="relative">
        <Input
          id="username"
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Enter username"
          maxLength={30}
          autoComplete="username"
          className="pr-10"
          aria-describedby="username-hint"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2" aria-hidden>
          {status.checking && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          {!status.checking && status.available === true && <CheckCircle className="h-4 w-4 text-success" />}
          {!status.checking && status.available === false && <XCircle className="h-4 w-4 text-destructive" />}
        </span>
      </div>
      {status.message && (
        <p role="status" className={cn('text-caption', status.available ? 'text-success' : status.available === false ? 'text-destructive' : 'text-muted-foreground')}>
          {status.message}
        </p>
      )}
      <p id="username-hint" className="text-caption text-muted-foreground">
        Letters, numbers, underscores and hyphens. 3 to 30 characters.
      </p>
    </div>
  )
}

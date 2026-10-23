'use client'

import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/form-label'

interface PasswordFieldProps {
  id: string
  label: React.ReactNode
  value: string
  onChange: (value: string) => void
  placeholder: string
  hint?: string
  required?: boolean
  autoComplete: 'current-password' | 'new-password'
  children?: React.ReactNode
}

export function PasswordField({ id, label, value, onChange, placeholder, hint, required, autoComplete, children }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          required={required}
          autoComplete={autoComplete}
          className="pr-11"
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-control text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {children}
      {hint && <p className="text-caption text-muted-foreground">{hint}</p>}
    </div>
  )
}

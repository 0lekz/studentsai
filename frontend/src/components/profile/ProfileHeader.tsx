/**
 * ProfileHeader: avatar, name, email; minimal, centered.
 */
'use client'

interface ProfileHeaderProps {
  name?: string
  email: string
}

export function ProfileHeader({ name = 'Profile', email }: ProfileHeaderProps) {
  const initials = (email || 'U').substring(0, 2).toUpperCase()
  return (
    <div className="mb-6 flex items-center justify-between">
      <div className="flex items-center gap-5">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#0f1115] text-orange-500 ring-1 ring-[#232a36]">
          <span className="text-lg font-semibold">{initials}</span>
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">{name}</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">{email}</p>
        </div>
      </div>
      <div className="text-xs text-gray-500 dark:text-gray-400" aria-hidden />
    </div>
  )
}



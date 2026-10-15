'use client'

import { AccountSettings } from '@/components/settings/AccountSettings'
import { AppearanceSettings } from '@/components/settings/AppearanceSettings'
import { ProfileSettings } from '@/components/settings/ProfileSettings'
import { SettingsSection } from '@/components/settings/SettingsSection'
import { useSession } from '@/components/shell/SessionProvider'

export default function SettingsPage() {
  const { user, setUser, logout } = useSession()

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-content px-gutter py-section">
        <h1 className="mb-8 text-headline font-semibold text-foreground">Settings</h1>
        <SettingsSection id="profile" title="Profile" description="Your username and password.">
          <ProfileSettings user={user} onUserUpdate={setUser} />
        </SettingsSection>
        <SettingsSection id="appearance" title="Appearance" description="Light, dark, or follow your device.">
          <AppearanceSettings />
        </SettingsSection>
        <SettingsSection id="account" title="Account" description="Sign out or delete your account.">
          <AccountSettings onSignOut={logout} />
        </SettingsSection>
      </div>
    </div>
  )
}

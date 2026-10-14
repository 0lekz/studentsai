/**
 * SettingsContent: Main content area for settings with tab-based rendering
 */
'use client'

import { ProfileSettings } from './ProfileSettings'
import { AppearanceSettings } from './AppearanceSettings'
import { GraphSettings } from './GraphSettings'
import { AISettings } from './AISettings'
import { StudyFlowSettings } from './StudyFlowSettings'
import { AdvancedSettings } from './AdvancedSettings'
import type { User } from '@/lib/api'

interface SettingsContentProps {
  activeTab: string
  user: User
  onUserUpdate: (user: User) => void
  searchQuery: string
}

export function SettingsContent({ activeTab, user, onUserUpdate }: SettingsContentProps) {
  const renderContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileSettings user={user} onUserUpdate={onUserUpdate} />
      case 'appearance':
        return <AppearanceSettings />
      case 'graph':
        return <GraphSettings />
      case 'ai':
        return <AISettings />
      case 'studyflow':
        return <StudyFlowSettings />
      case 'advanced':
        return <AdvancedSettings />
      default:
        return <ProfileSettings user={user} onUserUpdate={onUserUpdate} />
    }
  }

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-4xl">
        {renderContent()}
      </div>
    </div>
  )
}

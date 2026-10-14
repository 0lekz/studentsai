/**
 * SettingsSidebar: Navigation sidebar for settings with search functionality
 */
'use client'

import { Search, User, Palette, Network, Brain, BookOpen, Settings, Shield } from 'lucide-react'

interface SettingsSidebarProps {
  activeTab: string
  onTabChange: (tab: string) => void
  searchQuery: string
  onSearchChange: (query: string) => void
}

const settingsTabs = [
  { id: 'profile', label: 'Profile', icon: User, description: 'Username, email, password' },
  { id: 'appearance', label: 'Appearance', icon: Palette, description: 'Theme, font size, layout' },
  { id: 'graph', label: 'Graph View', icon: Network, description: 'Coming soon: customization options' },
  { id: 'ai', label: 'AI Features', icon: Brain, description: 'Coming soon: smart study assistance' },
  { id: 'studyflow', label: 'Study Flow', icon: BookOpen, description: 'Flashcard settings & learning' },
  { id: 'advanced', label: 'Advanced', icon: Settings, description: 'Coming soon: export & analytics' },
]

export function SettingsSidebar({ activeTab, onTabChange, searchQuery, onSearchChange }: SettingsSidebarProps) {
  const filteredTabs = settingsTabs.filter(tab => 
    tab.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tab.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="w-80 bg-white dark:bg-[#141820] border-r border-gray-200 dark:border-[#232a36] p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">Settings</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Customize your StudentsAI experience
        </p>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search settings..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-[#232a36] rounded-lg bg-gray-50 dark:bg-[#0f1115] text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
        />
      </div>

      {/* Navigation Tabs */}
      <nav className="space-y-1">
        {filteredTabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`w-full text-left p-3 rounded-lg transition-all duration-200 group ${
                isActive
                  ? 'bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800'
                  : 'hover:bg-gray-50 dark:hover:bg-[#0f1115] border border-transparent'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon 
                  className={`h-5 w-5 ${
                    isActive 
                      ? 'text-orange-600 dark:text-orange-400' 
                      : 'text-gray-400 group-hover:text-gray-600 dark:text-gray-500 dark:group-hover:text-gray-300'
                  }`} 
                />
                <div className="flex-1 min-w-0">
                  <div className={`font-medium ${
                    isActive 
                      ? 'text-orange-900 dark:text-orange-100' 
                      : 'text-gray-900 dark:text-gray-100'
                  }`}>
                    {tab.label}
                  </div>
                  <div className={`text-sm ${
                    isActive 
                      ? 'text-orange-700 dark:text-orange-300' 
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {tab.description}
                  </div>
                </div>
              </div>
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="absolute bottom-6 left-6 right-6">
        <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
          <Shield className="h-3 w-3" />
          <span>Your data is secure and private</span>
        </div>
      </div>
    </div>
  )
}

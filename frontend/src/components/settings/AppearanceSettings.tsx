/**
 * AppearanceSettings: Theme, font size, and layout customization
 */
'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Palette, Type, Layout, Clock } from 'lucide-react'
import { api, type SettingsAppearance } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'

export function AppearanceSettings() {
  const { toast } = useToast()
  const [settings, setSettings] = useState<SettingsAppearance>({
    theme: 'system',
    font_size: 'medium',
    layout_density: 'comfortable',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  // Load current settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const currentSettings = await api.getAppearanceSettings()
        setSettings(currentSettings)
      } catch (error) {
        console.error('Failed to load appearance settings:', error)
        // Use defaults if loading fails
      }
    }
    loadSettings()
  }, [])

  const handleThemeChange = (theme: 'light' | 'dark' | 'system') => {
    setSettings(prev => ({ ...prev, theme }))
    setHasChanges(true)
    
    // Apply theme immediately for better UX
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      document.documentElement.classList.toggle('dark', systemTheme === 'dark')
    } else {
      document.documentElement.classList.toggle('dark', theme === 'dark')
    }
  }

  const handleSave = async () => {
    setIsLoading(true)
    try {
      await api.updateAppearanceSettings(settings)
      setHasChanges(false)
      toast({
        title: "Appearance settings saved",
        description: "Your visual preferences have been updated.",
      })
    } catch {
      toast({
        title: "Error saving settings",
        description: "Failed to save your appearance preferences. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Appearance</h2>
        <p className="text-gray-600 dark:text-gray-400">
          Customize the look and feel of your learning environment
        </p>
      </div>

      {/* Theme Selection */}
      <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Palette className="h-5 w-5" />
            <span>Theme</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex space-x-2">
            <Button
              variant={settings.theme === 'light' ? 'default' : 'outline'}
              onClick={() => handleThemeChange('light')}
              className={`${
                settings.theme === 'light'
                  ? 'bg-orange-600 hover:bg-orange-700 text-white border-0'
                  : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 bg-white dark:bg-[#1d2430]'
              }`}
            >
              Light
            </Button>
            <Button
              variant={settings.theme === 'dark' ? 'default' : 'outline'}
              onClick={() => handleThemeChange('dark')}
              className={`${
                settings.theme === 'dark'
                  ? 'bg-orange-600 hover:bg-orange-700 text-white border-0'
                  : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 bg-white dark:bg-[#1d2430]'
              }`}
            >
              Dark
            </Button>
            <Button
              variant={settings.theme === 'system' ? 'default' : 'outline'}
              onClick={() => handleThemeChange('system')}
              className={`${
                settings.theme === 'system'
                  ? 'bg-orange-600 hover:bg-orange-700 text-white border-0'
                  : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 bg-white dark:bg-[#1d2430]'
              }`}
            >
              System
            </Button>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Choose your preferred color scheme. System follows your operating system preference.
          </p>
        </CardContent>
      </Card>

      {/* Typography - Coming Soon */}
      <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Type className="h-5 w-5" />
            <span>Typography</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-start space-x-2">
              <Clock className="h-5 w-5 text-gray-600 dark:text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-gray-700 dark:text-gray-300">
                <p className="font-medium">Coming Soon</p>
                <p className="mt-1">Font size, family, and typography customization options will be available in future updates.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Layout - Coming Soon */}
      <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Layout className="h-5 w-5" />
            <span>Layout</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-start space-x-2">
              <Clock className="h-5 w-5 text-gray-600 dark:text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-gray-700 dark:text-gray-300">
                <p className="font-medium">Coming Soon</p>
                <p className="mt-1">Layout density, sidebar preferences, and interface customization will be available in future updates.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Submit Button */}
      <div className="flex justify-end">
        <Button 
          onClick={handleSave} 
          disabled={isLoading || !hasChanges}
          className="bg-orange-600 hover:bg-orange-700 dark:bg-orange-600 dark:hover:bg-orange-700 text-white border-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>
    </div>
  )
}

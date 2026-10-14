/**
 * AISettings: AI feature configuration
 */
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Brain, Clock } from 'lucide-react'

export function AISettings() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">AI Features</h2>
        <p className="text-gray-600 dark:text-gray-400">
          AI-powered study assistance and smart features
        </p>
      </div>

      <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Brain className="h-5 w-5" />
            <span>AI Features</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-6 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-center">
            <div className="flex items-center justify-center space-x-2 mb-3">
              <Clock className="h-8 w-8 text-gray-600 dark:text-gray-400" />
              <span className="text-lg font-medium text-gray-700 dark:text-gray-300">Coming Soon</span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              We&apos;re working on AI-powered features to enhance your learning experience.
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500">
              Smart note summaries, intelligent flashcard generation, learning pattern analysis, and personalized study recommendations.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

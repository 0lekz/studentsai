'use client'

import { useState, useEffect } from 'react'
import { Header } from '@/components/layout/Header'
import FlashcardDashboard from '@/components/flashcards/FlashcardDashboard'
import { api, type User } from '@/lib/api'

export default function FlashcardsPage() {
  const [user, setUser] = useState<User | null>(null)
  const [stats, setStats] = useState({
    totalCards: 0,
    dueToday: 0,
    mastered: 0,
    learning: 0
  })

  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await api.getProfileSettings()
        setUser(userData)
        loadStats()
      } catch (error) {
        console.error('Failed to load user profile:', error)
      }
    }
    loadUser()
  }, [])

  const loadStats = async () => {
    try {
      const flashcards = await api.getUserFlashcards()
      const stats = {
        totalCards: flashcards.length,
        // FlashcardResponse carries no next-review date, so no card is ever counted as due
        dueToday: 0,
        mastered: flashcards.filter(f => (f.mastery_level || 0) >= 80).length,
        learning: flashcards.filter(f => (f.mastery_level || 0) < 80).length
      }
      setStats(stats)
    } catch (error) {
      console.error('Failed to load flashcard stats:', error)
    }
  }

  if (!user) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-[#0f1115]">
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-gray-500 dark:text-gray-400">Loading flashcards...</div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-[#0f1115]">
      {/* Header */}
      <Header 
        user={{ id: user.id, email: user.email, username: user.username || '', created_at: user.created_at }} 
        onLogout={() => { localStorage.clear(); window.location.replace('/landing') }}
        context="flashcards"
      />
      
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 bg-orange-500 rounded-xl">
              <img src="/flashcards-icon.svg" alt="Flashcards" className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Flashcards
              </h1>
              <p className="text-lg text-gray-600 dark:text-gray-400">
                Study and review your knowledge
              </p>
            </div>
          </div>
          
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.totalCards}</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.dueToday}</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Due Today</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.mastered}</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Mastered</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.learning}</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Learning</div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <FlashcardDashboard />
      </div>
    </main>
  )
}

'use client'

import { useEffect } from 'react'
import { Spinner } from '@/components/ui/spinner'

export default function RootPage() {
  useEffect(() => {
    window.location.replace(localStorage.getItem('authToken') ? '/today' : '/landing')
  }, [])

  return (
    <div className="flex h-dvh items-center justify-center bg-background">
      <Spinner label="Loading StudentsAI" />
    </div>
  )
}

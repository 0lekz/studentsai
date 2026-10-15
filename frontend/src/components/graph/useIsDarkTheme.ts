'use client'

import { useEffect, useState } from 'react'

export function useIsDarkTheme(): boolean {
  const [isDark, setIsDark] = useState(() => typeof document !== 'undefined' && document.documentElement.classList.contains('dark'))

  useEffect(() => {
    const html = document.documentElement
    const observer = new MutationObserver(() => setIsDark(html.classList.contains('dark')))
    observer.observe(html, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

  return isDark
}

'use client'

import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

const STEPS = [
  {
    title: 'Bring the course',
    description: 'Drop in lecture slides and PDFs. The key concepts come out in the order your professor teaches them.',
  },
  {
    title: 'Practice every day',
    description: 'Today lines up due reviews and your weakest concepts. Answer in your own words and get graded feedback.',
  },
  {
    title: 'Ask and check',
    description: 'Stuck on a slide? Ask, and the answer cites the page. The map shows how well you know each concept.',
  },
]

const STEP_INTERVAL_MS = 4000

export function HowItWorks() {
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const interval = setInterval(() => setActiveStep((step) => (step + 1) % STEPS.length), STEP_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="w-full">
      <div className="mb-14 text-center">
        <h2 className="text-4xl font-semibold text-foreground md:text-5xl">How it works</h2>
        <p className="mx-auto mt-6 max-w-3xl text-xl text-muted-foreground">
          From this week’s slides to knowing them, in three steps. No flashcards to type.
        </p>
      </div>

      <ol className="grid grid-cols-1 gap-6 md:grid-cols-3 md:gap-8">
        {STEPS.map((step, index) => (
          <li
            key={step.title}
            className={cn(
              'relative rounded-2xl border bg-surface p-8 transition-all duration-500',
              activeStep === index ? 'border-brand shadow-lg md:scale-[1.03]' : 'border-border'
            )}
          >
            <div className="mb-6 text-6xl font-light text-muted-foreground/40">{index + 1}</div>
            <h3 className="mb-3 text-xl font-semibold text-foreground">{step.title}</h3>
            <p className="leading-relaxed text-muted-foreground">{step.description}</p>
            {activeStep === index && <span aria-hidden className="absolute right-4 top-4 h-2 w-2 rounded-full bg-brand" />}
          </li>
        ))}
      </ol>
    </div>
  )
}

'use client'

import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MediaFrame } from '@/components/landing/MediaFrame'
import { screenshots } from '@/components/landing/screenshots'
import { ParticlesBackground } from '@/components/landing/ParticlesBackground'
import { ConstructionNotice } from '@/components/ui/construction-notice'
import { REPO_URL, UNDER_CONSTRUCTION } from '@/lib/launch'

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <ParticlesBackground count={90} />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.06] dark:opacity-[0.08]"
        style={{
          backgroundImage: 'linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      <div className="relative mx-auto max-w-7xl px-6 pb-20 pt-24 sm:pb-28 sm:pt-32">
        <div className="grid items-center gap-16 md:grid-cols-2">
          <div className="space-y-10">
            <ConstructionNotice className="animate-in fade-in max-w-xl" />
            <h1 className="animate-in fade-in slide-in-from-bottom-2 text-5xl font-extrabold tracking-tight text-foreground md:text-6xl lg:text-7xl">
              A tutor that has read your course
            </h1>
            <p className="animate-in fade-in slide-in-from-bottom-2 text-xl leading-relaxed text-muted-foreground delay-100 md:text-2xl">
              Drop in your lecture slides. StudentsAI asks you questions from them, grades your answers, and points to the exact slide you missed.
            </p>
            <div className="animate-in fade-in slide-in-from-bottom-2 flex flex-col gap-3 delay-200 sm:flex-row sm:items-center">
              {UNDER_CONSTRUCTION ? (
                <>
                  <Button asChild size="lg" className="h-14 rounded-[14px] px-8 text-lg">
                    <a href="#how-it-works">
                      See what is coming
                      <ArrowRight className="h-5 w-5" />
                    </a>
                  </Button>
                  <Button asChild variant="ghost" size="lg" className="h-14 px-6 text-lg text-muted-foreground">
                    <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
                      Follow the rebuild on GitHub
                    </a>
                  </Button>
                </>
              ) : (
                <>
                  <Button asChild size="lg" className="h-14 rounded-[14px] px-8 text-lg">
                    <Link href="/auth">
                      Start studying free
                      <ArrowRight className="h-5 w-5" />
                    </Link>
                  </Button>
                  <Button asChild variant="ghost" size="lg" className="h-14 px-6 text-lg text-muted-foreground">
                    <a href="#how-it-works">See how it works</a>
                  </Button>
                </>
              )}
            </div>
          </div>
          <div className="animate-in fade-in slide-in-from-bottom-2 flex items-end justify-end">
            <div className="md:translate-x-16 md:scale-110 lg:translate-x-24 lg:scale-125">
              <MediaFrame src={screenshots.practiceFeedback} alt="A practice question with graded feedback that cites the lecture slide" sizes="(min-width: 1024px) 900px, 100vw" priority />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

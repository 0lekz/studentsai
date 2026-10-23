import { Metadata } from 'next'
import { CalendarCheck, MessageCircleQuestion, Network, Repeat, Smartphone, Target } from 'lucide-react'
import { Hero } from '@/components/landing/Hero'
import { PublicHeader } from '@/components/landing/PublicHeader'
import { SiteFooter } from '@/components/landing/SiteFooter'
import { Section } from '@/components/landing/Section'
import { MediaFrame } from '@/components/landing/MediaFrame'
import { FeatureGrid } from '@/components/landing/FeatureGrid'
import { GetStarted } from '@/components/landing/GetStarted'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { ParallaxGrid } from '@/components/landing/ParallaxGrid'
import { screenshots } from '@/components/landing/screenshots'

export const metadata: Metadata = {
  title: 'StudentsAI - A tutor that has read your course',
  description: 'Drop in your lecture slides. StudentsAI quizzes you on them, grades your answers with feedback that cites the slide, and shows what to study next.',
}

const TODAY_POINTS = [
  { icon: Repeat, text: 'Spaced repetition across all your courses, so reviews come back right before you would forget' },
  { icon: Target, text: 'Your weakest concepts first, not the ones you already know' },
  { icon: Smartphone, text: 'One question per screen, made for the phone on the bus' },
]

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background" id="main">
      <PublicHeader />

      <Hero />

      <Section id="features" className="py-16">
        <div className="mx-auto mb-12 max-w-3xl text-center">
          <div className="mx-auto mb-6 h-px w-24 bg-border" />
          <h2 className="text-4xl font-semibold text-foreground md:text-5xl">The loop a good tutor runs</h2>
          <p className="mt-6 text-xl leading-relaxed text-muted-foreground md:text-2xl">
            It asks you questions, tells you what you missed and why, shows you where the answer lives, and remembers what you struggle with.
          </p>
        </div>

        <FeatureGrid
          features={[
            {
              src: screenshots.practiceFeedback,
              alt: 'Graded feedback on a typed answer, with the missing points and the source slide',
              title: 'Practice with real feedback',
              description: 'Answer in your own words. See what was right, what was missing, and the page the answer comes from.',
              icon: <CalendarCheck className="h-5 w-5" />,
            },
            {
              src: screenshots.askAnswer,
              alt: 'An answer to a question about the course, with numbered citations to the slides',
              title: 'Ask the course',
              description: 'Stuck on a slide? Ask. The answer uses your professor’s terms, cites the page, and says so when your files do not cover it.',
              icon: <MessageCircleQuestion className="h-5 w-5" />,
            },
            {
              src: screenshots.conceptMap,
              alt: 'A concept map of the course with mastery shown on every concept',
              title: 'Know where you stand',
              description: 'A map of the course’s concepts in teaching order, with your mastery on each one and what to study next.',
              icon: <Network className="h-5 w-5" />,
            },
          ]}
        />
      </Section>

      <ParallaxGrid>
        <Section className="py-20">
          <div className="flex flex-col items-center gap-12 lg:flex-row lg:gap-20">
            <div className="flex-1">
              <div className="mb-4 text-base uppercase tracking-[0.14em] text-muted-foreground">Twenty minutes a day</div>
              <h2 className="text-4xl font-semibold leading-tight text-foreground">Open Today, press one button</h2>
              <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
                Today gathers the questions that are due across your courses and your weakest concepts into one session. Do it at your desk or in transit.
              </p>
              <ul className="mt-8 space-y-4">
                {TODAY_POINTS.map(({ icon: Icon, text }) => (
                  <li key={text} className="flex items-start gap-3 text-foreground">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-brand-soft-foreground">
                      <Icon className="h-4 w-4" aria-hidden />
                    </span>
                    <span className="pt-1">{text}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="w-full max-w-sm lg:w-auto">
              <MediaFrame src={screenshots.today} alt="Today on a phone: the suggested session and the weakest concepts of a course" sizes="(min-width: 1024px) 384px, 100vw" className="shadow-xl" />
            </div>
          </div>
        </Section>
      </ParallaxGrid>

      <Section id="how-it-works" className="scroll-mt-16 py-20">
        <HowItWorks />
      </Section>

      <Section className="py-20">
        <GetStarted />
      </Section>

      <SiteFooter />
    </main>
  )
}

import { Metadata } from 'next'
import { Hero } from '@/components/landing/Hero'
import { PublicHeader } from '@/components/landing/PublicHeader'
import { SiteFooter } from '@/components/landing/SiteFooter'
import { Section } from '@/components/landing/Section'
import MiniGraph from '@/components/landing/MiniGraph'
import { MediaFrame } from '@/components/landing/MediaFrame'
import { FeatureGrid } from '@/components/landing/FeatureGrid'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { PricingCTA } from '@/components/landing/PricingCTA'
import { ParallaxGrid } from '@/components/landing/ParallaxGrid'
import { screenshots } from '@/components/landing/screenshots'

export const metadata: Metadata = {
  title: 'StudentsAI - Your Intelligent Study Companion',
  description: 'AI-powered study assistant for students. Create notes, generate summaries, flashcards, and visualize knowledge connections.',
}

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-[#0f1115]" id="main">
      <PublicHeader />
      
      <Hero />
      
      <ParallaxGrid>
        <Section id="features" className="py-10">
          <div className="grid gap-8 md:grid-cols-12 items-start relative">
            <div className="md:col-span-7">
              <MiniGraph height={600} />
              <div className="mt-3 text-sm uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">
                Interactive mini graph — drag to explore<span className="ml-2 inline-block w-6 h-[2px] align-middle bg-orange-500" aria-hidden="true"></span>
              </div>
            </div>
            <div className="md:col-span-5">
              <div className="text-base tracking-[0.14em] uppercase text-gray-500 dark:text-gray-400 mb-6">
                DISCOVER CONNECTIONS
              </div>
              <h2 className="font-semibold text-gray-900 dark:text-gray-100 text-5xl leading-tight">
                See how your ideas connect
              </h2>
              <p className="mt-6 text-gray-600 dark:text-gray-300 text-xl leading-relaxed">
                Backlinks and a visual graph help you jump between related concepts without losing context.
              </p>
            </div>
          </div>
        </Section>
      </ParallaxGrid>

      {/* Interactive Feature Grid */}
      <Section className="py-16">
        <div className="max-w-3xl mx-auto text-center mb-12">
          <div className="h-px w-24 mx-auto bg-gray-200 dark:bg-[#232a36] mb-6" />
          <h2 className="text-5xl font-semibold text-gray-900 dark:text-white">Built for modern studying</h2>
          <p className="mt-6 text-gray-600 dark:text-gray-300 text-2xl leading-relaxed">
            Generate flashcards, study with AI feedback, and see context from connected notes — all in one flow.
          </p>
        </div>
        
        <FeatureGrid
          features={[
            {
              src: screenshots.flashcardsView,
              alt: 'Contextual flashcards',
              title: 'Generate Contextual Flashcards',
              description: 'Generate flashcards using context of your notes and review them at any time.',
              icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              )
            },
            {
              src: screenshots.customizeYourGraphView,
              alt: 'Knowledge graph view',
              title: 'Expand Knowledge Context',
              description: 'Generate flashcards based on a graph of knowledge, not just single notes.',
              icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              )
            },
            {
              src: screenshots.getFeedbackOnYourAnswers,
              alt: 'AI evaluates your answer',
              title: 'AI Evaluation & Spaced Repetition',
              description: 'Evaluate your answers, get instant AI feedback, and master concepts with spaced repetition.',
              icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              )
            }
          ]}
        />
      </Section>

      {/* Transition Section with Background Change */}
      <div className="bg-gradient-to-b from-gray-50 to-white dark:from-[#0f1115] dark:to-[#141820] py-20">
        <div className="max-w-3xl mx-auto text-center mb-16">
          <h2 className="text-3xl font-semibold text-gray-900 dark:text-white mb-4">
            Ready to see it in action?
          </h2>
          <p className="text-gray-600 dark:text-gray-300 text-lg">
            Explore the powerful features that make StudentsAI the ultimate study companion.
          </p>
        </div>
      </div>

      {/* AI Summary + Backlinks Section */}
      <ParallaxGrid>
        <Section className="py-20" variant="fullWidth">
          <div className="flex flex-col lg:flex-row gap-12 items-center">
            <div className="flex-1">
              <MediaFrame
                src={screenshots.notesViewWithBacklinks}
                alt="AI Summary with backlinks"
                className="shadow-xl"
              />
            </div>
            <div className="flex-1">
              <h2 className="font-semibold text-gray-900 dark:text-gray-100 text-4xl leading-tight mb-6">
                AI Summary + Backlinks
              </h2>
              <p className="text-gray-600 dark:text-gray-300 text-lg leading-relaxed mb-6">
                Transform your notes into intelligent summaries with AI-powered insights and discover connections through backlinks.
              </p>
              <ul className="space-y-3 text-gray-700 dark:text-gray-300">
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  AI-generated summaries that capture key concepts
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  Automatic backlink discovery between related notes
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  Context-aware connections that enhance understanding
                </li>
              </ul>
            </div>
          </div>
        </Section>
      </ParallaxGrid>

      {/* Advanced Spaced Repetition Section */}
      <ParallaxGrid>
        <Section className="py-20" variant="fullWidth">
          <div className="flex flex-col lg:flex-row-reverse gap-12 items-center">
            <div className="flex-1">
              <MediaFrame
                src={screenshots.flashcardsDashboard}
                alt="Advanced spaced repetition dashboard"
                className="shadow-xl"
              />
            </div>
            <div className="flex-1">
              <h2 className="font-semibold text-gray-900 dark:text-gray-100 text-4xl leading-tight mb-4">
                Advanced Spaced Repetition Concepts
              </h2>
              <p className="text-gray-600 dark:text-gray-300 text-lg leading-relaxed mb-4">
                Master complex topics with scientifically-proven spaced repetition algorithms and intelligent scheduling.
              </p>
              <ul className="space-y-2 text-gray-700 dark:text-gray-300">
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  SM-2 algorithm with adaptive difficulty adjustment
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  Context-aware scheduling based on your learning patterns
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  Intelligent review timing for optimal retention
                </li>
              </ul>
            </div>
          </div>
        </Section>
      </ParallaxGrid>

      {/* Track Your Progress Section */}
      <ParallaxGrid>
        <Section className="py-20" variant="fullWidth">
          <div className="flex flex-col lg:flex-row gap-12 items-center">
            <div className="flex-1">
              <MediaFrame
                src={screenshots.trackYourActivity}
                alt="Progress tracking dashboard"
                className="shadow-xl"
              />
            </div>
            <div className="flex-1">
              <h2 className="font-semibold text-gray-900 dark:text-gray-100 text-4xl leading-tight mb-6">
                Track Your Progress
              </h2>
              <p className="text-gray-600 dark:text-gray-300 text-lg leading-relaxed mb-6">
                Monitor your learning journey with detailed analytics, progress insights, and performance metrics.
              </p>
              <ul className="space-y-3 text-gray-700 dark:text-gray-300">
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  Comprehensive learning analytics and insights
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  Progress tracking across all study sessions
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"/>
                  Performance metrics and improvement suggestions
                </li>
              </ul>
            </div>
          </div>
        </Section>
      </ParallaxGrid>

      {/* How It Works Section */}
      <Section className="py-20">
        <HowItWorks />
      </Section>

      {/* Pricing & CTA Section */}
      <Section className="py-20">
        <PricingCTA />
      </Section>

      <SiteFooter />
    </main>
  )
}



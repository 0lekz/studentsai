/**
 * Design rationale: Minimal, modern hero with a subtle Japanese 90s nod via thin borders and gentle motion.
 * It reuses the project's Tailwind + shadcn tokens (spacing, radius, orange #f97316 accent via Button) and typography.
 */
'use client'

import Link from 'next/link'
import { MediaFrame } from '@/components/landing/MediaFrame'
import { screenshots } from '@/components/landing/screenshots'
import { ParticlesBackground } from '@/components/landing/ParticlesBackground'

interface HeroProps {
	headline?: string
	subhead?: string
}

export function Hero({
  headline = 'Turn Your Notes into a Knowledge Network',
  subhead = 'StudentsAI links ideas with backlinks, keywords, and an interactive graph—so studying feels organized and fast.'
}: HeroProps) {

	return (
		<section className="relative overflow-hidden">
			<ParticlesBackground count={90} />
			<div
				aria-hidden
				className="pointer-events-none absolute inset-0 opacity-[0.06] dark:opacity-[0.08]"
				style={{
					backgroundImage:
						'linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)',
					backgroundSize: '24px 24px'
				}}
			/>

			<div className="relative mx-auto max-w-7xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-28">
				<div className="grid gap-16 md:grid-cols-2 items-center">
					<div className="space-y-10">
						<h1 className="animate-in fade-in slide-in-from-bottom-2 text-5xl font-extrabold tracking-tight text-gray-900 dark:text-gray-50 md:text-6xl lg:text-7xl">
							{headline}
						</h1>
						<p className="animate-in fade-in slide-in-from-bottom-2 delay-100 text-xl text-gray-600 dark:text-gray-300 md:text-2xl leading-relaxed">
							{subhead}
						</p>
						<div className="animate-in fade-in slide-in-from-bottom-2 delay-200">
							<Link href="/auth">
								<button
									className="inline-flex items-center gap-2 rounded-[14px] px-8 py-4 text-lg font-medium shadow-sm ring-1 ring-inset bg-orange-500 text-white ring-orange-500/30 transition-transform duration-150 ease-out hover:-translate-y-0.5 hover:shadow active:translate-y-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-orange-500 disabled:opacity-60 disabled:cursor-not-allowed"
									aria-busy={false}
								>
									{/* plus icon to avoid play-button feel */}
									<svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
									Start studying free
								</button>
							</Link>
						</div>
					</div>
					<div className="animate-in fade-in slide-in-from-bottom-2 flex justify-end items-end">
						<div className="transform scale-110 md:scale-125 lg:scale-150 translate-x-40 translate-y-4">
							<MediaFrame src={screenshots.notes} alt="Notes view screenshot" sizes="(min-width: 1024px) 900px, 100vw" priority />
						</div>
					</div>
				</div>
			</div>

			{/* Quick tour removed (modal) */}
		</section>
	)
}



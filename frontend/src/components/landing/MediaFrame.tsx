'use client'

import Image, { type StaticImageData } from 'next/image'

/**
 * MediaFrame: Minimalistic, rounded frame for screenshots.
 * - Clean, modern design with subtle borders
 * - Dark-ready with slight transparency
 * - Proper responsive sizing that maintains full image quality
 * - Images display at optimal size without artificial scaling
 */

interface MediaFrameProps {
	src?: StaticImageData
	alt: string
	priority?: boolean
	sizes?: string
	className?: string
}

export function MediaFrame({ src, alt, priority, sizes = '(min-width: 1024px) 50vw, 100vw', className = '' }: MediaFrameProps) {
	return (
		<div className={`rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden dark:bg-gray-900 dark:border-gray-700 ${className}`}>
			{src ? (
				<div className="relative flex justify-center">
					<Image
						src={src}
						alt={alt}
						priority={priority}
						sizes={sizes}
						className="block h-auto max-w-full object-contain"
					/>
				</div>
			) : (
				<div className="aspect-[16/10] w-full bg-gray-100 dark:bg-gray-800" aria-label={alt} />
			)}
		</div>
	)
}



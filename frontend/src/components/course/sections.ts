import { FileText, Layers, MessageCircleQuestion, Network, NotebookPen, type LucideIcon } from 'lucide-react'

export type CourseSectionSlug = 'materials' | 'practice' | 'ask' | 'map' | 'notes'

export const COURSE_SECTIONS: ReadonlyArray<{ slug: CourseSectionSlug; label: string; icon: LucideIcon }> = [
  { slug: 'materials', label: 'Materials', icon: FileText },
  { slug: 'practice', label: 'Practice', icon: Layers },
  { slug: 'ask', label: 'Ask', icon: MessageCircleQuestion },
  { slug: 'map', label: 'Map', icon: Network },
  { slug: 'notes', label: 'Notes', icon: NotebookPen },
]

export function activeSectionFrom(pathname: string): CourseSectionSlug | undefined {
  const slug = pathname.split('/')[3]
  return COURSE_SECTIONS.find((section) => section.slug === slug)?.slug
}

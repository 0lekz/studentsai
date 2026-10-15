'use client'

import { FlashcardDashboard } from '@/components/flashcards/FlashcardDashboard'
import { PracticeEmptyState } from '@/components/practice/PracticeEmptyState'
import { useCourse } from '@/components/course/CourseProvider'

export default function PracticePage() {
  const { course } = useCourse()
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-content px-gutter py-section">
        <FlashcardDashboard courseId={course.id} emptyState={<PracticeEmptyState courseId={course.id} />} />
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { api, type Flashcard, type FlashcardReviewResult, type Note } from '@/lib/api'
import { 
  RefreshCw,
  Tag,
  Clock,
  CheckCircle,
  Eye,
  EyeOff,
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  X
} from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { NotesGraph } from '@/components/graph/NotesGraph'

interface FlashcardViewerProps {
  noteId?: string
  note: Note
  onFlashcardCreated?: (flashcard: Flashcard) => void
}

export function FlashcardViewer({ noteId, note }: FlashcardViewerProps) {
  // Use noteId from props or extract from note object
  const actualNoteId = noteId || note.id
  const [flashcards, setFlashcards] = useState<Flashcard[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)
  const [userAnswer, setUserAnswer] = useState('')
  const [isReviewing, setIsReviewing] = useState(false)
  const [reviewResult, setReviewResult] = useState<FlashcardReviewResult | null>(null)
  const [showTagInput, setShowTagInput] = useState(false)
  const [newTag, setNewTag] = useState('')
  const [qualityRating, setQualityRating] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [viewType, setViewType] = useState<'all' | 'specific' | 'contextual'>('all')
  const removeEmojis = (text: string) => text.replace(/[\u{1F300}-\u{1FAFF}\u{1F600}-\u{1F64F}\u{2700}-\u{27BF}\u{2600}-\u{26FF}\u{FE0F}]/gu, '')

  const loadFlashcards = useCallback(async () => {
    if (!actualNoteId) return
    
    try {
      setLoading(true)
      const response = await api.getNoteFlashcards(actualNoteId)
      setFlashcards(response)
      setCurrentIndex(0)
      setShowAnswer(false)
      setUserAnswer('')
      setReviewResult(null)
    } catch (error) {
      console.error('Failed to load flashcards:', error)
    } finally {
      setLoading(false)
    }
  }, [actualNoteId])

  useEffect(() => {
    loadFlashcards()
  }, [actualNoteId, loadFlashcards])

  const specificList = flashcards.filter(fc => fc.flashcard_type !== 'contextual')
  const contextualList = flashcards.filter(fc => fc.flashcard_type === 'contextual')
  const viewList = viewType === 'all' ? flashcards : viewType === 'specific' ? specificList : contextualList

  const handleReview = async () => {
    const current = viewList[currentIndex]
    if (!userAnswer.trim() || !current) return

    try {
      setIsReviewing(true)
      const result = await api.reviewFlashcardEnhanced(
        current.id,
        userAnswer,
        qualityRating || undefined
      )
      setReviewResult(result)
      // Automatically show the answer after review so feedback is visible
      setShowAnswer(true)
    } catch (err) {
      console.error('Failed to review flashcard:', err)
    } finally {
      setIsReviewing(false)
    }
  }

  const addTag = async (tag: string) => {
    const current = viewList[currentIndex]
    if (!tag.trim() || !current) return

    try {
      await api.addFlashcardTag(current.id, tag.trim())
      setNewTag('')
      setShowTagInput(false)
      await loadFlashcards()
    } catch (err) {
      console.error('Failed to add tag:', err)
    }
  }

  const removeTag = async (tag: string) => {
    const current = viewList[currentIndex]
    if (!current) return

    try {
      await api.removeFlashcardTag(current.id, tag)
      await loadFlashcards()
    } catch (err) {
      console.error('Failed to remove tag:', err)
    }
  }

  const nextFlashcard = () => {
    const total = viewList.length
    if (currentIndex < total - 1) {
      setCurrentIndex(currentIndex + 1)
      setShowAnswer(false)
      setUserAnswer('')
      setReviewResult(null)
      setQualityRating(null)
    }
  }

  const previousFlashcard = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setShowAnswer(false)
      setUserAnswer('')
      setReviewResult(null)
      setQualityRating(null)
    }
  }

  const resetFlashcard = () => {
    setShowAnswer(false)
    setUserAnswer('')
    setReviewResult(null)
    setQualityRating(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    )
  }

  if (flashcards.length === 0) {
    return (
      <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardContent className="p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4">
            <img src="/icons/flashcards-icon.svg" alt="Flashcards" className="w-full h-full opacity-60" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            No flashcards yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Generate flashcards for this note to start studying
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button 
              onClick={async () => {
                try {
                  const generatedFlashcards = await api.generateNoteFlashcards(actualNoteId, 5)
                  setFlashcards(generatedFlashcards)
                  setCurrentIndex(0)
                  setShowAnswer(false)
                  setUserAnswer('')
                  setReviewResult(null)
                  setViewType('specific')
                } catch (error) {
                  console.error('Failed to generate flashcards:', error)
                }
              }}
              className="bg-orange-600 hover:bg-orange-700 text-white border-0 shadow-sm"
            >
              Generate Specific (single note)
            </Button>
            <Button 
              variant="outline"
              onClick={async () => {
                try {
                  const generated = await api.generateContextualFlashcards(actualNoteId, 10)
                  setFlashcards(generated)
                  setCurrentIndex(0)
                  setShowAnswer(false)
                  setUserAnswer('')
                  setReviewResult(null)
                  setViewType('contextual')
                } catch (error) {
                  console.error('Failed to generate contextual flashcards:', error)
                }
              }}
              className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800"
            >
              Generate Contextual (graph up to 5)
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  // If user filtered to a set that doesn't exist yet
  if (viewList.length === 0) {
    const isContextual = viewType === 'contextual'
    return (
      <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardContent className="p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4">
            <img src="/icons/flashcards-icon.svg" alt="Flashcards" className="w-full h-full opacity-60" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            No {isContextual ? 'contextual' : 'specific'} flashcards yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {isContextual
              ? 'Generate contextual flashcards using related notes from the graph.'
              : 'Generate specific flashcards from this single note.'}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {isContextual ? (
              <Button 
                onClick={async () => {
                  try {
                    const generated = await api.generateContextualFlashcards(actualNoteId, 10)
                    setFlashcards(generated)
                    setCurrentIndex(0)
                    setShowAnswer(false)
                    setUserAnswer('')
                    setReviewResult(null)
                    setViewType('contextual')
                  } catch (error) {
                    console.error('Failed to generate contextual flashcards:', error)
                  }
                }}
                className="bg-orange-600 hover:bg-orange-700 text-white border-0 shadow-sm"
              >
                Generate Contextual (graph up to 5)
              </Button>
            ) : (
              <Button 
                onClick={async () => {
                  try {
                    const generatedFlashcards = await api.generateNoteFlashcards(actualNoteId, 5)
                    setFlashcards(generatedFlashcards)
                    setCurrentIndex(0)
                    setShowAnswer(false)
                    setUserAnswer('')
                    setReviewResult(null)
                    setViewType('specific')
                  } catch (error) {
                    console.error('Failed to generate flashcards:', error)
                  }
                }}
                className="bg-orange-600 hover:bg-orange-700 text-white border-0 shadow-sm"
              >
                Generate Specific (single note)
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  const currentFlashcard = viewList[currentIndex]
  const isFirst = currentIndex === 0
  const isLast = currentIndex === viewList.length - 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-500 rounded-lg">
            <img src="/flashcards-icon.svg" alt="Flashcards" className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              Flashcard {currentIndex + 1} of {viewList.length}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {currentFlashcard.flashcard_type === 'contextual' ? 'Contextual' : 'Single Note'} Flashcard
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Tabs value={viewType} onValueChange={(v: string) => { const next = (v === 'all' || v === 'specific' || v === 'contextual') ? v : 'all'; setViewType(next); setCurrentIndex(0); setShowAnswer(false); setReviewResult(null); setUserAnswer(''); }}>
            <TabsList className="bg-gray-100 dark:bg-[#0f1115] dark:border dark:border-[#232a36]">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="specific">Specific</TabsTrigger>
              <TabsTrigger value="contextual">Contextual</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button 
            variant="outline" 
            size="sm"
            onClick={loadFlashcards}
            className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-colors shadow-sm bg-white dark:bg-gray-800"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div 
          className="bg-orange-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${viewList.length ? (((currentIndex + 1) / viewList.length) * 100) : 0}%` }}
        ></div>
      </div>

      {/* Flashcard Card */}
      <Card className="bg-white dark:bg-[#141820] border-gray-200 dark:border-[#232a36]">
        <CardContent className="p-8">
          {/* Question */}
          <div className={`${showAnswer ? 'hidden' : 'block'}`}>
            <div className="text-center space-y-6">
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="h-4 w-4" />
                Question
              </div>
              <h3 className="text-2xl font-medium text-gray-900 dark:text-gray-100 leading-relaxed">
                {currentFlashcard.question}
              </h3>

              {/* User Answer Input */}
              <div className="max-w-md mx-auto space-y-3">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 text-left">
                  Your Answer (Beta)
                </label>
                <Input
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  placeholder="Type your answer here..."
                  className="text-center text-lg bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100"
                />
                <Button
                  onClick={handleReview}
                  disabled={!userAnswer.trim() || isReviewing}
                  className="w-full bg-orange-600 hover:bg-orange-700 text-white border-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isReviewing ? 'Analyzing...' : 'Submit Answer'}
                </Button>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Beta feature: AI will analyze your answer and provide feedback
                </p>
              </div>
            </div>
          </div>

          {/* Answer */}
          <div className={`${showAnswer ? 'block' : 'hidden'}`}>
            <div className="text-center space-y-6">
              <div className="flex items-center justify-center gap-2 text-sm text-green-600 dark:text-green-400">
                <CheckCircle className="h-4 w-4" />
                Answer
              </div>
              <h3 className="text-2xl font-medium text-gray-900 dark:text-gray-100 leading-relaxed">
                {currentFlashcard.answer}
              </h3>

              {/* Review Result */}
              {reviewResult && (
                <div className="max-w-md mx-auto p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-blue-900 dark:text-blue-100">AI Feedback</h4>
                    <div className="inline-flex items-center gap-2 bg-blue-100 dark:bg-blue-900/60 px-3 py-1 rounded-full border border-blue-200 dark:border-blue-700">
                      <CheckCircle className="h-3.5 w-3.5 text-blue-700 dark:text-blue-300" />
                      <span className="text-xs text-blue-700 dark:text-blue-300 font-medium">
                        {reviewResult.verdict === 'correct' ? 'Excellent' : reviewResult.verdict === 'partial' ? 'Good' : 'Needs Work'}
                      </span>
                    </div>
                  </div>
                  <p className="text-blue-800 dark:text-blue-200 mb-3">{removeEmojis(reviewResult.feedback)}</p>
                  
                  <div className="grid grid-cols-3 gap-4 text-sm mb-1">
                    <div>
                      <span className="text-blue-700 dark:text-blue-300">Score:</span>
                      <div className="font-medium text-blue-900 dark:text-blue-100">
                        {reviewResult.ai_score}/100
                      </div>
                    </div>
                    <div>
                      <span className="text-blue-700 dark:text-blue-300">Quality:</span>
                      <div className="font-medium text-blue-900 dark:text-blue-100">
                        {reviewResult.verdict === 'correct' ? '5/5' : reviewResult.verdict === 'partial' ? '3/5' : '1/5'}
                      </div>
                    </div>
                    <div>
                      <span className="text-blue-700 dark:text-blue-300">Mastery:</span>
                      <div className="font-medium text-blue-900 dark:text-blue-100">
                        {currentFlashcard.mastery_level || 0}%
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tags */}
      {currentFlashcard.tags && currentFlashcard.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {currentFlashcard.tags.map(tag => (
            <Badge
              key={tag}
              variant="outline"
              className="cursor-pointer hover:bg-red-50 dark:hover:bg-red-950/30 border-gray-200 dark:border-[#232a36]"
              onClick={() => removeTag(tag)}
            >
              {tag} <X className="h-3 w-3 ml-1" />
            </Badge>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            onClick={() => setShowAnswer(!showAnswer)}
            variant="outline"
            className="flex items-center gap-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-colors shadow-sm bg-white dark:bg-gray-800"
          >
            {showAnswer ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            {showAnswer ? 'Hide Answer' : 'Show Answer'}
          </Button>

          <Button
            variant="outline"
            onClick={() => setShowTagInput(!showTagInput)}
            className="flex items-center gap-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-colors shadow-sm bg-white dark:bg-gray-800"
          >
            <Tag className="h-4 w-4" />
            Tags
          </Button>
        </div>

        {/* Quality Rating */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">Rate your performance:</span>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((rating) => (
              <Button
                key={rating}
                variant={qualityRating === rating ? "default" : "outline"}
                size="sm"
                onClick={() => setQualityRating(rating)}
                className={`w-8 h-8 p-0 ${
                  qualityRating === rating 
                    ? 'bg-orange-600 text-white border-orange-600 shadow-sm hover:bg-orange-700' 
                    : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 bg-white dark:bg-gray-800'
                }`}
              >
                {rating}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Tag Input */}
      {showTagInput && (
        <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-[#232a36]">
          <Input
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            placeholder="Enter new tag..."
            className="flex-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100"
            onKeyPress={(e) => e.key === 'Enter' && addTag(newTag)}
          />
          <Button
            onClick={() => addTag(newTag)}
            disabled={!newTag.trim()}
            size="sm"
            className="bg-orange-600 hover:bg-orange-700 text-white border-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Add
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowTagInput(false)}
            size="sm"
            className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-colors shadow-sm bg-white dark:bg-gray-800"
          >
            Cancel
          </Button>
        </div>
      )}

      {/* SRS Controls */}
      {reviewResult && (
        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-[#232a36]">
          <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">Spaced Repetition</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-700 dark:text-gray-300">E-Factor:</span>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {reviewResult.srs_data.efactor}
              </div>
            </div>
            <div>
              <span className="text-gray-700 dark:text-gray-300">Interval:</span>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {reviewResult.srs_data.interval_days} days
              </div>
            </div>
            <div>
              <span className="text-gray-700 dark:text-gray-300">Repetitions:</span>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {reviewResult.srs_data.repetitions}
              </div>
            </div>
            <div>
              <span className="text-gray-700 dark:text-gray-300">Next Review:</span>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {new Date(reviewResult.next_review_date).toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="outline" 
            size="sm"
            onClick={previousFlashcard}
            disabled={isFirst}
            className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm bg-white dark:bg-gray-800"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={nextFlashcard}
            disabled={isLast}
            className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm bg-white dark:bg-gray-800"
          >
            Next
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={resetFlashcard}
            className="border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-colors shadow-sm bg-white dark:bg-gray-800"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
        </div>
      </div>

      {/* Mini Graph Context (simple, non-distracting) */}
      <div className="rounded-lg border border-gray-200 dark:border-[#232a36] bg-white dark:bg-[#141820] p-2">
        <NotesGraph onNodeClick={() => {}} highlightNodeIds={[actualNoteId]} mode="mini" anchorNodeId={actualNoteId} />
      </div>
    </div>
  )
}


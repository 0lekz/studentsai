'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { 
  Lightbulb, 
  Copy, 
  RefreshCw, 
  FileText, 
  TrendingDown,
  Loader2
} from 'lucide-react'
import Image from 'next/image'
import { api } from '@/lib/api'

interface SummaryViewerProps {
  text: string
  onClose: () => void
}

export function SummaryViewer({ text, onClose }: SummaryViewerProps) {
  const [summary, setSummary] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [stats, setStats] = useState({
    originalWords: 0,
    summaryWords: 0,
    compressionRatio: 0
  })

  const generateSummary = async () => {
    setIsLoading(true)
    setError('')
    
    try {
      const response = await api.summarizeText(text)
      // API returns { summary, word_count, original_length }
      setSummary(response.summary)
      const originalWords = text.split(/\s+/).filter(Boolean).length
      const summaryWords = response.word_count
      setStats({
        originalWords,
        summaryWords,
        compressionRatio: Math.round((1 - summaryWords / Math.max(1, originalWords)) * 100)
      })
    } catch {
      setError('Failed to generate summary')
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(summary)
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  const getCompressionColor = (ratio: number) => {
    if (ratio >= 70) return 'text-green-600'
    if (ratio >= 50) return 'text-yellow-600'
    return 'text-orange-600'
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
          <Image src="/icons/summary-icon.svg" alt="Summary" width={28} height={28} />
          <span>AI Summary</span>
        </h2>
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </div>

      {/* Original Text */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-lg">
            <FileText className="h-5 w-5" />
            <span>Original Text</span>
            <span className="text-sm font-normal text-gray-500">
              ({text.split(/\s+/).length} words)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-40 overflow-y-auto">
            <p className="text-sm text-gray-700 leading-relaxed">
              {text}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Summary Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2 text-lg">
              <Lightbulb className="h-5 w-5 text-orange-500" />
              <span>Summary</span>
            </CardTitle>
            <div className="flex items-center space-x-2">
              {summary && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={copyToClipboard}
                  className="flex items-center space-x-2"
                >
                  <Copy className="h-4 w-4" />
                  <span>Copy</span>
                </Button>
              )}
              <Button
                onClick={generateSummary}
                disabled={isLoading}
                className="flex items-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    <span>{summary ? 'Regenerate' : 'Generate'} Summary</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
          
          {summary ? (
            <div className="space-y-4">
              <Textarea
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                className="min-h-[200px] text-base leading-relaxed"
                placeholder="Summary will appear here..."
              />
              
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{stats.originalWords}</div>
                  <div className="text-sm text-gray-600">Original Words</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{stats.summaryWords}</div>
                  <div className="text-sm text-gray-600">Summary Words</div>
                </div>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${getCompressionColor(stats.compressionRatio)}`}>
                    {stats.compressionRatio}%
                  </div>
                  <div className="text-sm text-gray-600 flex items-center justify-center space-x-1">
                    <TrendingDown className="h-3 w-3" />
                    <span>Compression</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12">
              <Lightbulb className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No summary yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                Click &quot;Generate Summary&quot; to create an AI-powered summary of your text.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tips */}
      <Card className="bg-orange-50 border-orange-200">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <Lightbulb className="h-5 w-5 text-orange-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-orange-900">Summary Tips</h4>
              <ul className="mt-1 text-sm text-orange-800 space-y-1">
                <li>• Summaries capture key concepts and main ideas</li>
                <li>• You can edit the generated summary to better fit your needs</li>
                <li>• Higher compression ratios indicate more concise summaries</li>
                <li>• Use summaries for quick review and study preparation</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://api.studentsai.org')

export interface User {
  id: string
  email: string
  username: string
  has_password?: boolean
  created_at: string
}

export interface UserProfileUpdate {
  username?: string
  email?: string
  current_password?: string
  new_password?: string
}

export interface UsernameCheck {
  username: string
  available: boolean
}

export interface SettingsAppearance {
  theme: 'light' | 'dark' | 'system'
  font_size: 'small' | 'medium' | 'large'
  layout_density: 'compact' | 'dense' | 'comfortable'
}

export interface SettingsGraph {
  edge_thickness_scale: number
  node_spacing: number
  show_backlinks: boolean
  physics_enabled: boolean
  clustering_strength: number
}

export interface SettingsAI {
  use_openai: boolean
  daily_request_limit: number
  enable_caching: boolean
}

export interface SettingsStudyFlow {
  quiz_enabled: boolean
  flashcard_auto_review: boolean
  linked_notes_suggestions: boolean
}

export interface SettingsAdvanced {
  data_export_enabled: boolean
  analytics_enabled: boolean
}

export interface Note {
  id: string
  title: string
  content: string
  summary?: string | null
  created_at: string
  updated_at: string
  tags?: string[]
}

export interface Flashcard {
  id: string
  question: string
  answer: string
  difficulty: number
  last_reviewed?: string
  created_at: string
  flashcard_type: string
  context_notes?: string[]
  tags?: string[]
  review_count: number
  mastery_level: number
  last_performance?: number
}

export interface FlashcardSRSData {
  flashcard_id: string
  efactor: number
  interval_days: number
  due_date: string
  repetitions: number
  next_review_date: string
}

export interface FlashcardSetInfo {
  id: string
  mode: string
  seed_note_id: string
  neighbor_note_ids: string[]
  created_at: string
  flashcard_count: number
}

export interface FlashcardReviewResult {
  flashcard_id: string
  ai_score: number
  verdict: string
  feedback: string
  missing_points: string[]
  confidence: number
  next_review_date: string
  srs_data: FlashcardSRSData
  tags_updated: string[]
}

export interface FlashcardGenerationResponse {
  flashcard_set_id: string
  cards: Flashcard[]
  context_notes: string[]
  total_tokens_used?: number
}

export interface GraphNode {
  id: string
  title: string
  content_preview: string
  created_at: string
  word_count: number
}

export interface GraphConnection {
  source_id: string
  target_id: string
  similarity: number
  connection_type: string
}

export interface GraphData {
  nodes: GraphNode[]
  connections: GraphConnection[]
  total_nodes: number
}

// Profile/stat types
export type EventType = 'NOTE_CREATED' | 'NOTE_REVIEWED' | 'FLASHCARD_CREATED' | 'FLASHCARD_REVIEWED'

export interface ProfileSummary {
  notes_created: number
  notes_reviewed: number
  flashcards_created: number
  flashcards_reviewed: number
  current_streak: number
  best_streak: number
  activity_7d: number
  activity_30d: number
}

export interface ActivityDayCount {
  date: string // YYYY-MM-DD UTC
  count: number
  top_type?: EventType
}

export interface ActivityResponse {
  from_date: string
  to_date: string
  kind: 'all' | 'notes' | 'flashcards'
  days: ActivityDayCount[]
}

export interface EventItem {
  id: string
  event_type: EventType
  occurred_at: string
  target_id?: string
  metadata?: Record<string, unknown>
}

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'APIError'
  }
}

class APIClient {
  private baseURL: string
  private token: string | null = null

  constructor(baseURL: string) {
    this.baseURL = baseURL
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('authToken')
    }
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('authToken', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
    }
  }

  async refreshToken(): Promise<boolean> {
    try {
      const response = await this.request<{ access_token: string; user: User }>('/auth/refresh', {
        method: 'POST',
      })
      
      if (response.access_token) {
        this.setToken(response.access_token)
        return true
      }
      return false
    } catch (error) {
      console.error('Token refresh failed:', error)
      this.clearToken()
      return false
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    isRetry: boolean = false
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    const headers = new Headers({ 'Content-Type': 'application/json' })
    if (options.headers) {
      const incoming = new Headers(options.headers as HeadersInit)
      incoming.forEach((value, key) => headers.set(key, value))
    }
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`)
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    // Handle 401 errors with automatic token refresh
    if (!response.ok && response.status === 401 && !isRetry && this.token) {
      console.log('Token expired, attempting refresh...')
      const refreshSuccess = await this.refreshToken()
      
      if (refreshSuccess) {
        // Retry the original request with the new token
        console.log('Token refreshed, retrying request...')
        return this.request<T>(endpoint, options, true)
      } else {
        // Refresh failed, redirect to login
        console.log('Token refresh failed, redirecting to login...')
        if (typeof window !== 'undefined') {
          window.location.replace('/landing')
        }
        throw new APIError(401, 'Authentication failed')
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new APIError(
        response.status,
        errorData.detail || errorData.error || 'An error occurred'
      )
    }

    return response.json()
  }

  // Upload image (multipart)
  async uploadImage(file: File): Promise<{ url: string; filename: string; content_type: string }> {
    const form = new FormData()
    form.append('file', file)
    const headers: Headers = new Headers()
    if (this.token) headers.set('Authorization', `Bearer ${this.token}`)
    const resp = await fetch(`${this.baseURL}/upload/image`, {
      method: 'POST',
      headers,
      body: form,
    })
    if (!resp.ok) {
      const errorData = await resp.json().catch(() => ({} as unknown))
      throw new APIError(resp.status, errorData.detail || 'Upload failed')
    }
    return resp.json()
  }

  // Auth endpoints
  async register(email: string, password: string, username: string) {
    const response = await this.request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, username }),
    })
    
    if (response.access_token) {
      this.setToken(response.access_token)
    }
    
    return response
  }

  async login(email: string, password: string) {
    const response = await this.request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    
    if (response.access_token) {
      this.setToken(response.access_token)
    }
    
    return response
  }

  async googleAuth(code: string) {
    const response = await this.request<{ access_token: string; user: User }>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
    
    if (response.access_token) {
      this.setToken(response.access_token)
    }
    
    return response
  }

  // Note endpoints
  async getNotes(): Promise<{ notes: Note[] }> {
    return this.request('/notes')
  }

  async getNote(id: string): Promise<Note> {
    return this.request(`/notes/${id}`)
  }

  async getSuggestedKeywords(noteId: string): Promise<{ note_id: string; keywords: string[] }> {
    return this.request(`/notes/${noteId}/keywords`)
  }

  async extractKeywords(noteId: string): Promise<Note> {
    return this.request(`/notes/${noteId}/extract-keywords`, {
      method: 'POST',
    })
  }

  async getBacklinks(noteId: string): Promise<Array<{ note_id: string; title: string; excerpt?: string; created_at: string }>> {
    return this.request(`/notes/${noteId}/backlinks`)
  }

  async createNote(title: string, content: string): Promise<Note> {
    return this.request('/notes', {
      method: 'POST',
      body: JSON.stringify({ title, content }),
    })
  }

  async updateNote(id: string, data: Partial<Pick<Note, 'title' | 'content' | 'summary'>>): Promise<Note> {
    return this.request(`/notes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteNote(id: string): Promise<void> {
    await this.request(`/notes/${id}`, {
      method: 'DELETE',
    })
  }

  async updateTags(noteId: string, tags: string[]): Promise<Note> {
    return this.request(`/notes/${noteId}/tags`, {
      method: 'PUT',
      body: JSON.stringify({ tags }),
    })
  }

  // AI endpoints
  async summarizeText(content: string): Promise<{ summary: string; word_count: number; original_length: number }> {
    return this.request('/ai/summarize', {
      method: 'POST',
      body: JSON.stringify({ content }),
    })
  }

  async generateFlashcards(content: string, count: number = 5): Promise<{ flashcards: Array<{ question: string; answer: string }>; count: number }> {
    return this.request('/ai/flashcards', {
      method: 'POST',
      body: JSON.stringify({ content, count }),
    })
  }

  async summarizeNote(id: string): Promise<Note> {
    return this.request(`/notes/${id}/summarize`, {
      method: 'POST',
    })
  }

  // Flashcard endpoints
  async getNoteFlashcards(noteId: string): Promise<Flashcard[]> {
    return this.request(`/notes/${noteId}/flashcards`)
  }

  async generateNoteFlashcards(noteId: string, count: number = 5): Promise<Flashcard[]> {
    return this.request(`/notes/${noteId}/flashcards/generate?count=${count}`, {
      method: 'POST',
    })
  }

  // Enhanced flashcard endpoints
  async getUserFlashcards(tags?: string[], search?: string): Promise<Flashcard[]> {
    const params = new URLSearchParams()
    if (tags && tags.length > 0) {
      params.append('tags', tags.join(','))
    }
    if (search && search.trim()) {
      params.append('search', search.trim())
    }
    
    const url = params.toString() ? `/flashcards/user?${params.toString()}` : '/flashcards/user'
    return this.request(url)
  }

  async getDueFlashcards(limit: number = 20): Promise<Flashcard[]> {
    return this.request(`/flashcards/due?limit=${limit}`)
  }

  async reviewFlashcard(flashcardId: string, userAnswer: string, performanceScore?: number): Promise<{ message: string; performance_score: number; feedback: string; mastery_level: number; next_review_date?: string; tags_updated: string[] }> {
    return this.request(`/flashcards/${flashcardId}/review`, {
      method: 'POST',
      body: JSON.stringify({
        flashcard_id: flashcardId,
        user_answer: userAnswer,
        performance_score: performanceScore
      }),
    })
  }

  async addFlashcardTag(flashcardId: string, tag: string): Promise<{ message: string; tags: string[] }> {
    return this.request(`/flashcards/${flashcardId}/tags/${tag}`, {
      method: 'POST',
    })
  }

  async removeFlashcardTag(flashcardId: string, tag: string): Promise<{ message: string; tags: string[] }> {
    return this.request(`/flashcards/${flashcardId}/tags/${tag}`, {
      method: 'DELETE',
    })
  }

  async generateContextualFlashcards(noteId: string, count: number = 10): Promise<Flashcard[]> {
    return this.request(`/notes/${noteId}/flashcards/contextual/generate?count=${count}`, {
      method: 'POST',
    })
  }

  // Enhanced flashcard system endpoints
  async generateFlashcardsEnhanced(
    mode: 'single' | 'context',
    noteId: string,
    count?: number,
    neighbors?: number,
    tokenCap?: number
  ): Promise<FlashcardGenerationResponse> {
    return this.request('/flashcards/generate', {
      method: 'POST',
      body: JSON.stringify({
        mode,
        note_id: noteId,
        count,
        neighbors,
        token_cap: tokenCap
      }),
    })
  }

  async reviewFlashcardEnhanced(
    flashcardId: string,
    typedAnswer: string,
    qualityRating?: number
  ): Promise<FlashcardReviewResult> {
    return this.request(`/flashcards/${flashcardId}/review/enhanced`, {
      method: 'POST',
      body: JSON.stringify({
        flashcard_id: flashcardId,
        typed_answer: typedAnswer,
        quality_rating: qualityRating
      }),
    })
  }

  async getFlashcardSets(): Promise<FlashcardSetInfo[]> {
    return this.request('/flashcards/sets')
  }

  async getDueFlashcardsSRS(limit: number = 20): Promise<Flashcard[]> {
    return this.request(`/flashcards/due/srs?limit=${limit}`)
  }

  async archiveMasteredFlashcards(minRepetitions: number = 3): Promise<{ message: string; flashcards: Array<{ id: string; question: string; tags: string[] }> }> {
    return this.request('/flashcards/archive/mastered', {
      method: 'POST',
      body: JSON.stringify({ min_repetitions: minRepetitions }),
    })
  }

  // Graph endpoint
  async getNotesGraph(): Promise<GraphData> {
    return this.request('/graph')
  }

  // Profile/stat endpoints
  async getProfileSummary(): Promise<ProfileSummary> {
    return this.request('/api/profile/summary')
  }

  async getRecentEvents(): Promise<EventItem[]> {
    return this.request('/api/profile/recent')
  }

  async getProfileActivity(fromISODate: string, toISODate: string, kind: 'all' | 'notes' | 'flashcards' = 'all'): Promise<ActivityResponse> {
    const params = new URLSearchParams({ from_date: fromISODate, to_date: toISODate, kind })
    return this.request(`/api/profile/activity?${params.toString()}`)
  }

  // Settings endpoints
  async getProfileSettings(): Promise<User> {
    return this.request('/api/settings/profile')
  }

  async updateProfileSettings(data: UserProfileUpdate): Promise<User> {
    return this.request('/api/settings/profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async sendEmailChangeVerification(newEmail: string): Promise<{ message: string }> {
    return this.request('/auth/send-email-change-verification', {
      method: 'POST',
      body: JSON.stringify({ new_email: newEmail }),
    })
  }

  async checkUsernameAvailability(username: string): Promise<UsernameCheck> {
    return this.request(`/api/settings/username/check/${username}`)
  }

  async getAppearanceSettings(): Promise<SettingsAppearance> {
    return this.request('/api/settings/appearance')
  }

  async updateAppearanceSettings(settings: SettingsAppearance): Promise<SettingsAppearance> {
    return this.request('/api/settings/appearance', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    })
  }

  async getGraphSettings(): Promise<SettingsGraph> {
    return this.request('/api/settings/graph')
  }

  async updateGraphSettings(settings: SettingsGraph): Promise<SettingsGraph> {
    return this.request('/api/settings/graph', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    })
  }

  async getAISettings(): Promise<SettingsAI> {
    return this.request('/api/settings/ai')
  }

  async updateAISettings(settings: SettingsAI): Promise<SettingsAI> {
    return this.request('/api/settings/ai', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    })
  }

  async getStudyFlowSettings(): Promise<SettingsStudyFlow> {
    return this.request('/api/settings/studyflow')
  }

  async updateStudyFlowSettings(settings: SettingsStudyFlow): Promise<SettingsStudyFlow> {
    return this.request('/api/settings/studyflow', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    })
  }

  async getAdvancedSettings(): Promise<SettingsAdvanced> {
    return this.request('/api/settings/advanced')
  }

  async updateAdvancedSettings(settings: SettingsAdvanced): Promise<SettingsAdvanced> {
    return this.request('/api/settings/advanced', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    })
  }

  // Account deletion
  async requestAccountDeletion(): Promise<{ message: string }> {
    return this.request('/auth/request-account-deletion', {
      method: 'POST',
    })
  }

  async confirmAccountDeletion(token: string): Promise<{ message: string }> {
    return this.request('/auth/confirm-account-deletion', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
  }
}

export const api = new APIClient(API_BASE_URL)

export { APIError }
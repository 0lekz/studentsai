import type { components, paths } from './api.generated'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://api.studentsai.org')

type Schemas = components['schemas']
type HttpMethod = 'get' | 'post' | 'put' | 'patch' | 'delete'
type Operation<P extends keyof paths, M extends HttpMethod> = NonNullable<paths[P][M]>
type JsonOf<R> = R extends { content: { 'application/json': infer Body } } ? Body : void
type SuccessOf<O> = O extends { responses: infer R }
  ? 200 extends keyof R
    ? JsonOf<R[200]>
    : 201 extends keyof R
      ? JsonOf<R[201]>
      : void
  : never
type JsonBodyOf<O> = O extends { requestBody?: { content: { 'application/json': infer Body } } } ? Body : never
type QueryOf<O> = O extends { parameters: { query?: infer Query } } ? NonNullable<Query> : never

export type ApiResponse<P extends keyof paths, M extends HttpMethod> = SuccessOf<Operation<P, M>>
export type ApiJsonBody<P extends keyof paths, M extends HttpMethod> = JsonBodyOf<Operation<P, M>>
export type ApiQuery<P extends keyof paths, M extends HttpMethod> = QueryOf<Operation<P, M>>

export type User = Schemas['UserResponse']
export type UserProfileUpdate = Schemas['UserProfileUpdate']
export type UsernameCheck = ApiResponse<'/api/settings/username/check/{username}', 'get'>
export type SettingsAppearance = Schemas['SettingsAppearance']
export type Note = Schemas['NoteResponse']
export type Flashcard = Schemas['FlashcardResponse']
export type FlashcardReviewResult = ApiResponse<'/flashcards/{flashcard_id}/review', 'post'>
export type GraphData = ApiResponse<'/graph', 'get'>
export type GraphNode = GraphData['nodes'][number]
export type GraphConnection = GraphData['connections'][number]
export type DocumentSummary = ApiResponse<'/documents', 'get'>[number]
export type DocumentChunk = ApiResponse<'/documents/{document_id}/chunks', 'get'>[number]

export type Course = Schemas['CourseResponse']
export type CourseListItem = Schemas['CourseListItem']
export type CourseCreate = Schemas['CourseCreate']
export type CourseUpdate = Schemas['CourseUpdate']

export type Concept = Schemas['ConceptResponse']
export type ConceptSource = Schemas['ConceptSourceResponse']
export type ConceptMap = Schemas['ConceptMapResponse']
export type ConceptMapNode = Schemas['ConceptMapNode']
export type ConceptMapEdge = Schemas['ConceptMapEdge']
export type ConceptEdgeKind = Schemas['ConceptEdgeKind']

export type QuestionKind = Schemas['FlashcardKind']
export type Verdict = Schemas['Verdict']
export type PracticeQuestion = Schemas['PracticeQuestion']
export type QuestionSource = Schemas['QuestionSource']
export type Citation = Schemas['Citation']
export type AnswerBody = Schemas['AnswerRequest']
export type AnswerResult = Schemas['AnswerResponse']
export type SrsState = Schemas['SrsState']
export type AskResult = Schemas['AskResponse']
export type TodaySummary = Schemas['TodayResponse']
export type TodayCourse = Schemas['TodayCourse']

type AuthResponse = ApiResponse<'/auth/login', 'post'>

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'APIError'
  }
}

function withQuery(path: string, query: Record<string, string | number | boolean | undefined | null>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.append(key, String(value))
  }
  const search = params.toString()
  return search ? `${path}?${search}` : path
}

function errorMessage(errorData: unknown): string {
  if (errorData && typeof errorData === 'object') {
    const { detail, error } = errorData as { detail?: unknown; error?: unknown }
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === 'string') return detail[0].msg
    if (typeof error === 'string') return error
  }
  return 'An error occurred'
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

  hasToken(): boolean {
    return Boolean(this.token)
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
      const response = await this.request<ApiResponse<'/auth/refresh', 'post'>>('/auth/refresh', {
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
    const headers = new Headers(options.headers)
    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`)
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, { ...options, headers })

    if (response.status === 401 && !isRetry && this.token) {
      const refreshed = await this.refreshToken()
      if (refreshed) {
        return this.request<T>(endpoint, options, true)
      }
      if (typeof window !== 'undefined') {
        window.location.replace('/landing')
      }
      throw new APIError(401, 'Authentication failed')
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new APIError(response.status, errorMessage(errorData))
    }

    if (response.status === 204) {
      return undefined as T
    }
    return response.json()
  }

  private storeAuth(response: AuthResponse) {
    if (response.access_token) {
      this.setToken(response.access_token)
    }
    return response
  }

  // Auth
  async register(email: string, password: string, username: string) {
    return this.storeAuth(await this.request<ApiResponse<'/auth/register', 'post'>>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, username }),
    }))
  }

  async login(email: string, password: string) {
    return this.storeAuth(await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }))
  }

  async googleAuth(code: string) {
    const response = await this.request<ApiResponse<'/auth/google', 'post'>>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
    if (response.access_token) {
      this.setToken(response.access_token)
    }
    return response
  }

  // Courses
  async getCourses(): Promise<ApiResponse<'/courses', 'get'>> {
    return this.request('/courses')
  }

  async getCourse(id: string): Promise<ApiResponse<'/courses/{course_id}', 'get'>> {
    return this.request(`/courses/${id}`)
  }

  async createCourse(body: ApiJsonBody<'/courses', 'post'>): Promise<ApiResponse<'/courses', 'post'>> {
    return this.request('/courses', { method: 'POST', body: JSON.stringify(body) })
  }

  async updateCourse(id: string, body: ApiJsonBody<'/courses/{course_id}', 'patch'>): Promise<ApiResponse<'/courses/{course_id}', 'patch'>> {
    return this.request(`/courses/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
  }

  async deleteCourse(id: string): Promise<void> {
    await this.request(`/courses/${id}`, { method: 'DELETE' })
  }

  // Documents
  async getDocuments(courseId: string): Promise<ApiResponse<'/documents', 'get'>> {
    const query: ApiQuery<'/documents', 'get'> = { course_id: courseId }
    return this.request(withQuery('/documents', query))
  }

  async uploadDocument(courseId: string, file: File): Promise<ApiResponse<'/documents', 'post'>> {
    const fields: Record<keyof Schemas['Body_upload_document_documents_post'], string | Blob> = { file, course_id: courseId }
    const form = new FormData()
    for (const [name, value] of Object.entries(fields)) form.append(name, value)
    return this.request('/documents', { method: 'POST', body: form })
  }

  async deleteDocument(id: string): Promise<void> {
    await this.request(`/documents/${id}`, { method: 'DELETE' })
  }

  async getDocumentChunks(documentId: string): Promise<DocumentChunk[]> {
    return this.request(`/documents/${documentId}/chunks`)
  }

  // Concepts
  async getConcepts(courseId: string): Promise<ApiResponse<'/courses/{course_id}/concepts', 'get'>> {
    return this.request(`/courses/${courseId}/concepts`)
  }

  async extractConcepts(courseId: string): Promise<ApiResponse<'/courses/{course_id}/concepts/extract', 'post'>> {
    return this.request(`/courses/${courseId}/concepts/extract`, { method: 'POST' })
  }

  async getConceptMap(courseId: string): Promise<ConceptMap> {
    return this.request(`/courses/${courseId}/map`)
  }

  async renameConcept(courseId: string, conceptId: string, name: string): Promise<Concept> {
    const body: ApiJsonBody<'/courses/{course_id}/concepts/{concept_id}', 'patch'> = { name }
    return this.request(`/courses/${courseId}/concepts/${conceptId}`, { method: 'PATCH', body: JSON.stringify(body) })
  }

  async deleteConcept(courseId: string, conceptId: string): Promise<void> {
    await this.request(`/courses/${courseId}/concepts/${conceptId}`, { method: 'DELETE' })
  }

  // Tutor
  async getToday(): Promise<TodaySummary> {
    return this.request('/today')
  }

  async startPracticeSession(courseId: string, size?: number): Promise<PracticeQuestion[]> {
    const body: ApiJsonBody<'/courses/{course_id}/practice/session', 'post'> = size === undefined ? null : { size }
    const session: ApiResponse<'/courses/{course_id}/practice/session', 'post'> = await this.request(`/courses/${courseId}/practice/session`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
    return session.questions
  }

  async generateQuestions(courseId: string, body: ApiJsonBody<'/courses/{course_id}/questions/generate', 'post'>): Promise<PracticeQuestion[]> {
    const generated: ApiResponse<'/courses/{course_id}/questions/generate', 'post'> = await this.request(`/courses/${courseId}/questions/generate`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
    return generated.questions
  }

  async answerQuestion(questionId: string, body: AnswerBody): Promise<AnswerResult> {
    return this.request(`/questions/${questionId}/answer`, { method: 'POST', body: JSON.stringify(body) })
  }

  async askCourse(courseId: string, question: string): Promise<AskResult> {
    const body: ApiJsonBody<'/courses/{course_id}/ask', 'post'> = { question }
    return this.request(`/courses/${courseId}/ask`, { method: 'POST', body: JSON.stringify(body) })
  }

  // Self-graded fallback for recall questions, which are stored as flashcards on the SM-2 schedule.
  async selfGradeQuestion(questionId: string, quality: number): Promise<SrsState> {
    const { due_date, interval_days, repetitions } = await this.reviewFlashcard(questionId, quality)
    return { due_date, interval_days, repetitions }
  }

  // Notes
  async getNotes(courseId?: string): Promise<ApiResponse<'/notes', 'get'>> {
    const query: ApiQuery<'/notes', 'get'> = { course_id: courseId }
    return this.request(withQuery('/notes', query))
  }

  async createNote(title: string, content: string, courseId?: string): Promise<ApiResponse<'/notes', 'post'>> {
    const body: ApiJsonBody<'/notes', 'post'> = { title, content, course_id: courseId }
    return this.request('/notes', { method: 'POST', body: JSON.stringify(body) })
  }

  async updateNote(id: string, data: ApiJsonBody<'/notes/{note_id}', 'put'>): Promise<ApiResponse<'/notes/{note_id}', 'put'>> {
    return this.request(`/notes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteNote(id: string): Promise<void> {
    await this.request(`/notes/${id}`, { method: 'DELETE' })
  }

  async summarizeNote(id: string): Promise<ApiResponse<'/notes/{note_id}/summarize', 'post'>> {
    return this.request(`/notes/${id}/summarize`, { method: 'POST' })
  }

  async summarizeText(content: string): Promise<ApiResponse<'/ai/summarize', 'post'>> {
    return this.request('/ai/summarize', {
      method: 'POST',
      body: JSON.stringify({ content }),
    })
  }

  // Flashcards
  async getNoteFlashcards(noteId: string): Promise<ApiResponse<'/notes/{note_id}/flashcards', 'get'>> {
    return this.request(`/notes/${noteId}/flashcards`)
  }

  async generateNoteFlashcards(noteId: string, count: number = 5): Promise<ApiResponse<'/notes/{note_id}/flashcards/generate', 'post'>> {
    const query: ApiQuery<'/notes/{note_id}/flashcards/generate', 'post'> = { count }
    return this.request(withQuery(`/notes/${noteId}/flashcards/generate`, query), { method: 'POST' })
  }

  async getUserFlashcards(filters: { tags?: string[]; search?: string; courseId?: string } = {}): Promise<ApiResponse<'/flashcards/user', 'get'>> {
    const query: ApiQuery<'/flashcards/user', 'get'> = {
      tags: filters.tags?.length ? filters.tags.join(',') : undefined,
      search: filters.search?.trim() || undefined,
      course_id: filters.courseId,
    }
    return this.request(withQuery('/flashcards/user', query))
  }

  async getDueFlashcards(limit: number = 20): Promise<ApiResponse<'/flashcards/due/srs', 'get'>> {
    const query: ApiQuery<'/flashcards/due/srs', 'get'> = { limit }
    return this.request(withQuery('/flashcards/due/srs', query))
  }

  async reviewFlashcard(flashcardId: string, qualityRating: number): Promise<FlashcardReviewResult> {
    const body: ApiJsonBody<'/flashcards/{flashcard_id}/review', 'post'> = { quality_rating: qualityRating }
    return this.request(`/flashcards/${flashcardId}/review`, { method: 'POST', body: JSON.stringify(body) })
  }

  async addFlashcardTag(flashcardId: string, tag: string): Promise<unknown> {
    return this.request(`/flashcards/${flashcardId}/tags/${encodeURIComponent(tag)}`, { method: 'POST' })
  }

  async removeFlashcardTag(flashcardId: string, tag: string): Promise<unknown> {
    return this.request(`/flashcards/${flashcardId}/tags/${encodeURIComponent(tag)}`, { method: 'DELETE' })
  }

  // Graph
  async getNotesGraph(courseId?: string): Promise<GraphData> {
    const query: ApiQuery<'/graph', 'get'> = { course_id: courseId }
    return this.request(withQuery('/graph', query))
  }

  // Settings
  async getProfileSettings(): Promise<User> {
    return this.request('/api/settings/profile')
  }

  async updateProfileSettings(data: UserProfileUpdate): Promise<ApiResponse<'/api/settings/profile', 'patch'>> {
    return this.request('/api/settings/profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async sendEmailChangeVerification(newEmail: string): Promise<ApiResponse<'/auth/send-email-change-verification', 'post'>> {
    const body: ApiJsonBody<'/auth/send-email-change-verification', 'post'> = { new_email: newEmail }
    return this.request('/auth/send-email-change-verification', { method: 'POST', body: JSON.stringify(body) })
  }

  async verifyEmailChange(token: string): Promise<ApiResponse<'/auth/verify-email-change', 'post'>> {
    const body: ApiJsonBody<'/auth/verify-email-change', 'post'> = { token }
    return this.request('/auth/verify-email-change', { method: 'POST', body: JSON.stringify(body) })
  }

  async checkUsernameAvailability(username: string): Promise<UsernameCheck> {
    return this.request(`/api/settings/username/check/${encodeURIComponent(username)}`)
  }

  async getAppearanceSettings(): Promise<SettingsAppearance> {
    return this.request('/api/settings/appearance')
  }

  async updateAppearanceSettings(settings: SettingsAppearance): Promise<ApiResponse<'/api/settings/appearance', 'patch'>> {
    return this.request('/api/settings/appearance', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    })
  }

  // Account
  async requestAccountDeletion(): Promise<ApiResponse<'/auth/request-account-deletion', 'post'>> {
    return this.request('/auth/request-account-deletion', { method: 'POST' })
  }
}

export const api = new APIClient(API_BASE_URL)

export { APIError }

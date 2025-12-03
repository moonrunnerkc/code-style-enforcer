// Author: Bradley R. Kinnard — talk to the backend

const API_BASE = '/api/v1'

// stored in localStorage so it persists across sessions
let apiKey = localStorage.getItem('api_key') || 'dev'

export function setApiKey(key: string) {
  apiKey = key
  localStorage.setItem('api_key', key)
}

export function getApiKey(): string {
  return apiKey
}

export interface Suggestion {
  id: string
  agent: string
  type: string
  message: string
  severity: number       // 1-5: impact level (Info → Critical)
  confidence: number     // 0.0-1.0: model's certainty
  score: number          // after RL weighting
  rated?: boolean        // has user submitted feedback?
  accepted?: boolean     // user feedback: true=accept, false=reject, undefined=not rated
}

export interface AgentWeights {
  [agent: string]: number
}

export interface AnalysisResult {
  analysis_id: string
  code_hash: string
  from_cache: boolean
  suggestions: Suggestion[]
  agent_weights: AgentWeights
  request_id: string
}

export interface FeedbackResponse {
  status: string
  message: string
  request_id: string
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>
  }

  // add auth header unless dev mode
  if (apiKey && apiKey !== 'dev') {
    headers['Authorization'] = `Bearer ${apiKey}`
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }

  return res.json()
}

export async function analyzeCode(
  code: string,
  language: string = 'python',
  detailLevel: string = 'normal'
): Promise<AnalysisResult> {
  return request<AnalysisResult>('/analyze', {
    method: 'POST',
    body: JSON.stringify({
      code,
      language,
      detail_level: detailLevel
    })
  })
}

export async function submitFeedback(
  analysisId: string,
  suggestionId: string,
  agent: string,
  accepted: boolean,
  userRating: number
): Promise<FeedbackResponse> {
  return request<FeedbackResponse>('/feedback', {
    method: 'POST',
    body: JSON.stringify({
      analysis_id: analysisId,
      suggestion_id: suggestionId,
      agent,
      accepted,
      user_rating: userRating
    })
  })
}

export async function getWeights(): Promise<AgentWeights> {
  return request<AgentWeights>('/agents/weights')
}

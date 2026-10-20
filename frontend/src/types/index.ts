export type Difficulty = 'Easy' | 'Medium' | 'Hard'

export interface StudentSummary {
  student_id: string
  name: string
  overall_mastery: number
  current_difficulty: Difficulty
}

export interface QuizHistoryEntry {
  quiz_id: string
  topic_id: string
  difficulty: Difficulty
  score: number
  total_questions: number
  timestamp: string
}

export interface StudentProfile extends StudentSummary {
  topic_mastery: Record<string, number>
  weak_topics: string[]
  strong_topics: string[]
  quiz_history: QuizHistoryEntry[]
}

export interface Topic {
  topic_id: string
  title: string
  kind: 'built_in' | 'upload'
  pages?: number
  chunks?: number
}

export interface Material {
  id: string
  title: string
  filename: string
  pages: number
  chunks: number
  created_at: string
}

export interface Citation {
  chunk_id: string
  title: string
  snippet: string
  similarity_score: number
  page?: number
  document_id?: string
}

export interface Explanation {
  topic_name: string
  summary: string
  conceptual_breakdown: string[]
  code_example?: string
  common_pitfalls: string[]
  citations: Citation[]
  model_name: string
  disclaimer: string
}

export interface Quiz {
  quiz_id: string
  topic_id: string
  topic_name: string
  difficulty: Difficulty
  questions: { question_id: string; prompt: string; options: string[] }[]
  citations: Citation[]
  model_name: string
}

export interface QuizResult {
  score_percentage: number
  correct_count: number
  total_questions: number
  previous_difficulty: Difficulty
  new_difficulty: Difficulty
  updated_mastery: number
  pedagogical_advice: string
  feedback: {
    question_id: string
    prompt: string
    selected_option_text: string
    correct_option_text: string
    is_correct: boolean
    explanation: string
    diagnosis: string
    source_chunk_id?: string
  }[]
}

export interface ModelStatus {
  available: boolean
  model: string
  message: string
}

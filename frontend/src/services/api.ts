import type { Explanation, Material, ModelStatus, Quiz, QuizResult, StudentProfile, StudentSummary, Topic } from '../types'

const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`)
  }
  return response.status === 204 ? undefined as T : response.json()
}

const json = (body: unknown) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  status: () => request<ModelStatus>('/api/status'),
  students: () => request<StudentSummary[]>('/api/students'),
  student: (id: string) => request<StudentProfile>(`/api/students/${encodeURIComponent(id)}`),
  createStudent: (name: string) => request<StudentProfile>('/api/students', json({ name })),
  topics: (id: string) => request<Topic[]>(`/api/materials/topics?student_id=${encodeURIComponent(id)}`),
  materials: (id: string) => request<Material[]>(`/api/materials?student_id=${encodeURIComponent(id)}`),
  upload: (id: string, file: File) => {
    const body = new FormData()
    body.append('student_id', id)
    body.append('file', file)
    return request<Material>('/api/materials', { method: 'POST', body })
  },
  deleteMaterial: (id: string, studentId: string) => request<void>(`/api/materials/${encodeURIComponent(id)}?student_id=${encodeURIComponent(studentId)}`, { method: 'DELETE' }),
  explain: (studentId: string, topicId: string) => request<Explanation>('/api/explanation/generate', json({ student_id: studentId, topic_id: topicId })),
  quiz: (studentId: string, topicId: string) => request<Quiz>('/api/assessment/quiz', json({ student_id: studentId, topic_id: topicId, question_count: 3 })),
  submit: (studentId: string, quiz: Quiz, answers: Record<string, number>) => request<QuizResult>('/api/assessment/submit', json({
    student_id: studentId, quiz_id: quiz.quiz_id, topic_id: quiz.topic_id,
    answers: quiz.questions.map(question => ({ question_id: question.question_id, selected_option_index: answers[question.question_id] }))
  }))
}

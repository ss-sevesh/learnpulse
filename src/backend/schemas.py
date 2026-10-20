from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

# Difficulty Levels
DifficultyLevel = Literal["Easy", "Medium", "Hard"]
BloomLevel = Literal["Recall", "Comprehension", "Application", "Analysis", "Synthesis", "Evaluation"]

# --- Syllabus & RAG Chunks ---
class SyllabusChunk(BaseModel):
    chunk_id: str
    section_id: str
    topic_id: str
    topic_name: str
    title: str
    content: str
    bloom_level: str
    grade_level: str

class Citation(BaseModel):
    chunk_id: str
    section_id: str
    topic_name: str
    title: str
    snippet: str
    similarity_score: float
    document_id: Optional[str] = None
    page: Optional[int] = None

class RAGSearchRequest(BaseModel):
    query: str
    topic_id: Optional[str] = None
    limit: int = 3

class RAGSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[Citation]

# --- Student Profile & History ---
class QuizHistoryEntry(BaseModel):
    quiz_id: str
    topic_id: str
    difficulty: DifficultyLevel
    score: float
    total_questions: int
    correct_answers: int
    timestamp: str

class StudentProfile(BaseModel):
    student_id: str
    name: str
    roll_no: str
    grade_level: str
    target_track: str
    overall_mastery: float
    current_difficulty: DifficultyLevel
    topic_mastery: Dict[str, float]
    weak_topics: List[str]
    strong_topics: List[str]
    quiz_history: List[QuizHistoryEntry] = Field(default_factory=list)

class StudentSummary(BaseModel):
    student_id: str
    name: str
    roll_no: str
    overall_mastery: float
    current_difficulty: DifficultyLevel
    weak_topics_count: int

# --- Explanation & Study Generation ---
class ExplanationRequest(BaseModel):
    student_id: str
    topic_id: str
    focus_area: Optional[str] = None

class ExplanationResponse(BaseModel):
    topic_id: str
    topic_name: str
    student_name: str
    difficulty: DifficultyLevel
    summary: str
    conceptual_breakdown: List[str]
    code_example: Optional[str] = None
    common_pitfalls: List[str]
    citations: List[Citation]
    llm_source: Literal["ollama"] = "ollama"
    model_name: str = ""
    disclaimer: str = "AI-generated study aid. Check claims against the cited excerpts."

# --- Quiz & Assessment ---
class QuizQuestion(BaseModel):
    question_id: str
    difficulty: DifficultyLevel
    prompt: str
    options: List[str] = Field(min_length=4, max_length=4)
    correct_option_index: int = Field(ge=0, le=3)
    explanation: str
    misconception_diagnoses: Dict[str, str] = Field(default_factory=dict)
    source_chunk_id: Optional[str] = None

class QuizQuestionPublic(BaseModel):
    question_id: str
    difficulty: DifficultyLevel
    prompt: str
    options: List[str]

class QuizGenerationRequest(BaseModel):
    student_id: str
    topic_id: str
    question_count: int = 3

class Quiz(BaseModel):
    quiz_id: str
    topic_id: str
    topic_name: str
    difficulty: DifficultyLevel
    questions: List[QuizQuestionPublic]
    citations: List[Citation] = Field(default_factory=list)
    llm_source: Literal["ollama"] = "ollama"
    model_name: str = ""

class QuizAnswerSubmission(BaseModel):
    question_id: str
    selected_option_index: int

class QuizSubmissionRequest(BaseModel):
    student_id: str
    quiz_id: str
    topic_id: str
    answers: List[QuizAnswerSubmission]

class QuestionFeedback(BaseModel):
    question_id: str
    prompt: str
    selected_option_index: int
    selected_option_text: str
    correct_option_index: int
    correct_option_text: str
    is_correct: bool
    explanation: str
    diagnosis: str
    source_chunk_id: Optional[str] = None

class QuizSubmissionResponse(BaseModel):
    quiz_id: str
    student_id: str
    topic_id: str
    topic_name: str
    score_percentage: float
    total_questions: int
    correct_count: int
    feedback: List[QuestionFeedback]
    previous_difficulty: DifficultyLevel
    new_difficulty: DifficultyLevel
    difficulty_action: Literal["PROMOTED", "RETAINED", "SUPPORT_STEP_DOWN"]
    mastery_delta: float
    updated_mastery: float
    pedagogical_advice: str

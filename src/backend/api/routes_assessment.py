import json
import uuid
from threading import Lock

from fastapi import APIRouter, HTTPException

from src.backend import storage
from src.backend.services.material_service import resolve_topic
from src.backend.config import settings
from src.backend.rag.qdrant_store import get_qdrant_store
from src.backend.schemas import Quiz, QuizGenerationRequest, QuizQuestionPublic, QuizSubmissionRequest, QuizSubmissionResponse
from src.backend.services.assessment_service import get_assessment_service
from src.backend.services.ollama_service import questions
from src.backend.services.student_service import get_student_service

router = APIRouter(prefix="/api/assessment", tags=["Practice"])
_submit_lock = Lock()


@router.post("/quiz", response_model=Quiz)
def generate_quiz(req: QuizGenerationRequest):
    if not 1 <= req.question_count <= 5:
        raise HTTPException(status_code=422, detail="Choose between 1 and 5 questions.")
    topic_name, owner = resolve_topic(req.topic_id, req.student_id)
    student = get_student_service().get_student(req.student_id)
    difficulty = student.current_difficulty
    citations = get_qdrant_store().search_syllabus(
        query=f"{topic_name} definitions mechanisms examples", topic_id=req.topic_id,
        profile_id=owner, limit=5)
    if not citations:
        raise HTTPException(status_code=422, detail="No indexed text was found for this topic.")
    generated = questions(topic_name, difficulty, citations, req.question_count)
    quiz_id = f"QZ-{uuid.uuid4().hex}"
    with storage.database() as db:
        db.execute("INSERT INTO quizzes VALUES (?, ?, ?, ?, NULL)",
                   (quiz_id, req.student_id, req.topic_id, json.dumps([q.model_dump() for q in generated])))
    return Quiz(quiz_id=quiz_id, topic_id=req.topic_id, topic_name=topic_name,
                difficulty=difficulty, questions=[QuizQuestionPublic.model_validate(q.model_dump()) for q in generated],
                citations=citations, model_name=settings.ollama_model)


@router.post("/submit", response_model=QuizSubmissionResponse)
def submit_quiz(req: QuizSubmissionRequest):
    with _submit_lock:
        return _submit_once(req)


def _submit_once(req: QuizSubmissionRequest):
    topic_name, _ = resolve_topic(req.topic_id, req.student_id)
    with storage.database() as db:
        row = db.execute("SELECT * FROM quizzes WHERE id = ? AND profile_id = ? AND topic_id = ?",
                         (req.quiz_id, req.student_id, req.topic_id)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found for this profile and topic.")
    if row["result"]:
        return QuizSubmissionResponse.model_validate_json(row["result"])
    try:
        result, updated_profile = get_assessment_service().evaluate_quiz(req)
        result.topic_name = topic_name
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with storage.database() as db:
        db.execute("UPDATE profiles SET data = ? WHERE id = ?", (updated_profile.model_dump_json(), req.student_id))
        db.execute("UPDATE quizzes SET result = ? WHERE id = ?", (result.model_dump_json(), req.quiz_id))
    get_student_service().cache_student(updated_profile)
    return result

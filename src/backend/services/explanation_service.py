from fastapi import HTTPException

from src.backend.services.material_service import resolve_topic
from src.backend.config import settings
from src.backend.rag.qdrant_store import get_qdrant_store
from src.backend.schemas import ExplanationRequest, ExplanationResponse
from src.backend.services.ollama_service import explain
from src.backend.services.student_service import get_student_service


class ExplanationService:
    def generate_explanation(self, req: ExplanationRequest) -> ExplanationResponse:
        topic_name, owner = resolve_topic(req.topic_id, req.student_id)
        student = get_student_service().get_student(req.student_id)
        citations = get_qdrant_store().search_syllabus(
            query=f"{topic_name} {req.focus_area or 'core concepts'}",
            topic_id=req.topic_id, profile_id=owner, limit=4)
        if not citations:
            raise HTTPException(status_code=422, detail="No indexed text was found for this topic.")
        content = explain(topic_name, student.current_difficulty, citations, req.focus_area)
        return ExplanationResponse(
            topic_id=req.topic_id, topic_name=topic_name, student_name=student.name,
            difficulty=student.current_difficulty, citations=citations,
            model_name=settings.ollama_model,
            disclaimer="AI-generated study aid. Check claims against the cited excerpts.",
            **content.model_dump())


_instance = ExplanationService()


def get_explanation_service():
    return _instance

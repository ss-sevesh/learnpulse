from fastapi import APIRouter
from src.backend.schemas import ExplanationRequest, ExplanationResponse
from src.backend.services.explanation_service import get_explanation_service

router = APIRouter(prefix="/api/explanation", tags=["Explanation Service"])

@router.post("/generate", response_model=ExplanationResponse)
def generate_grounded_explanation(req: ExplanationRequest):
    """
    Generate an AI concept explanation grounded in Qdrant syllabus chunks,
    calibrated to the student's mastery level with traceable citations.
    """
    service = get_explanation_service()
    return service.generate_explanation(req)

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.backend.schemas import StudentProfile, StudentSummary
from src.backend.services.student_service import get_student_service

router = APIRouter(prefix="/api/students", tags=["Students"])

class CreateStudentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)

@router.get("", response_model=List[StudentSummary])
async def list_students():
    """Retrieve summaries of all students in cohort."""
    service = get_student_service()
    return service.get_all_summaries()

@router.post("", response_model=StudentProfile, status_code=201)
def create_student(req: CreateStudentRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Enter a profile name.")
    return get_student_service().create_student(name)

@router.get("/{student_id}", response_model=StudentProfile)
async def get_student_detail(student_id: str):
    """Retrieve full profile, mastery distribution, and quiz history for a student."""
    service = get_student_service()
    student = service.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found.")
    return student

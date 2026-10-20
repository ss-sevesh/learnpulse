import logging
from typing import List, Optional, Dict
from src.backend import storage
from src.backend.schemas import StudentProfile, StudentSummary

logger = logging.getLogger(__name__)

class StudentService:
    def __init__(self):
        self._students: Dict[str, StudentProfile] = {}
        self.cohort_id: str = "CSE-2026-SEM5"
        self._load_students()

    def _load_students(self):
        storage.initialize()
        for profile in storage.list_profiles():
            self._students[profile.student_id] = profile

        logger.info(f"Loaded {len(self._students)} student profiles into memory.")

    def get_all_students(self) -> List[StudentProfile]:
        return list(self._students.values())

    def get_all_summaries(self) -> List[StudentSummary]:
        return [
            StudentSummary(
                student_id=s.student_id,
                name=s.name,
                roll_no=s.roll_no,
                overall_mastery=s.overall_mastery,
                current_difficulty=s.current_difficulty,
                weak_topics_count=len(s.weak_topics)
            )
            for s in self._students.values()
        ]

    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        return self._students.get(student_id)

    def cache_student(self, updated_profile: StudentProfile):
        self._students[updated_profile.student_id] = updated_profile

    def create_student(self, name: str) -> StudentProfile:
        profile = storage.create_profile(name)
        self._students[profile.student_id] = profile
        return profile

# Global singleton
_student_service_instance: Optional[StudentService] = None

def get_student_service() -> StudentService:
    global _student_service_instance
    if _student_service_instance is None:
        _student_service_instance = StudentService()
    return _student_service_instance

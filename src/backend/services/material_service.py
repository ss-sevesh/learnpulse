"""Resolve topics within a selected local profile."""
from fastapi import HTTPException

from src.backend import storage
from src.backend.rag.chunker import load_all_syllabus_chunks
from src.backend.services.student_service import get_student_service


def require_profile(student_id: str):
    if not get_student_service().get_student(student_id):
        raise HTTPException(status_code=404, detail="Profile not found.")


def get_material(document_id: str, student_id: str):
    with storage.database() as db:
        row = db.execute("SELECT * FROM materials WHERE id = ? AND profile_id = ?", (document_id, student_id)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Material not found in this profile.")
    return dict(row)


def resolve_topic(topic_id: str, student_id: str):
    require_profile(student_id)
    if topic_id.startswith("DOC-"):
        material = get_material(topic_id, student_id)
        return material["title"], student_id
    built_in = {chunk.topic_id: chunk.topic_name for chunk in load_all_syllabus_chunks()}
    if topic_id not in built_in:
        raise HTTPException(status_code=404, detail="Topic not found.")
    return built_in[topic_id], None

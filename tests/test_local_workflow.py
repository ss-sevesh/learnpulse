"""Local profile, material, and assessment boundaries without a live model."""
import uuid
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from src.backend import storage
from src.backend.api import routes_assessment, routes_materials
from src.backend.main import app
from src.backend.rag.qdrant_store import QdrantSyllabusStore
from src.backend.schemas import QuizQuestion
from src.backend.services import student_service
from src.backend.services import explanation_service
from src.backend.services.ollama_service import ExplanationContent


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite3")
    monkeypatch.setattr(routes_materials, "UPLOAD_DIR", tmp_path / "uploads")
    storage.initialize()
    monkeypatch.setattr(student_service, "_student_service_instance", None)
    store = QdrantSyllabusStore(in_memory=True)
    monkeypatch.setattr(routes_materials, "get_qdrant_store", lambda: store)
    monkeypatch.setattr(routes_assessment, "get_qdrant_store", lambda: store)
    monkeypatch.setattr(explanation_service, "get_qdrant_store", lambda: store)
    monkeypatch.setattr(explanation_service, "explain", lambda *args: ExplanationContent(
        summary="A clear explanation based on the selected source excerpt.",
        conceptual_breakdown=["First supported concept", "Second supported concept"],
        common_pitfalls=["A common mistake"]))
    def fake_questions(topic, difficulty, citations, count):
        return [QuizQuestion(question_id=f"Q-{uuid.uuid4().hex}", difficulty=difficulty,
                             prompt="Which statement follows from the source?",
                             options=["Correct", "Wrong A", "Wrong B", "Wrong C"],
                             correct_option_index=0, explanation="The source supports Correct.",
                             misconception_diagnoses={"1": "Wrong", "2": "Wrong", "3": "Wrong"},
                             source_chunk_id=citations[0].chunk_id) for _ in range(count)]
    monkeypatch.setattr(routes_assessment, "questions", fake_questions)
    return TestClient(app)


def test_profiles_and_materials_are_scoped(client):
    first = client.post("/api/students", json={"name": "First"}).json()["student_id"]
    second = client.post("/api/students", json={"name": "Second"}).json()["student_id"]
    uploaded = client.post("/api/materials", data={"student_id": first},
                           files={"file": ("notes.txt", b"Recursion uses a base case. " * 30, "text/plain")})
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()["id"]
    assert document_id in [topic["topic_id"] for topic in client.get("/api/materials/topics", params={"student_id": first}).json()]
    assert document_id not in [topic["topic_id"] for topic in client.get("/api/materials/topics", params={"student_id": second}).json()]
    assert client.post("/api/explanation/generate", json={"student_id": second, "topic_id": document_id}).status_code == 404
    own = client.post("/api/explanation/generate", json={"student_id": first, "topic_id": document_id})
    assert own.status_code == 200, own.text
    assert own.json()["citations"][0]["document_id"] == document_id
    assert client.delete(f"/api/materials/{document_id}", params={"student_id": second}).status_code == 404
    assert client.delete(f"/api/materials/{document_id}", params={"student_id": first}).status_code == 204


def test_quiz_validates_and_persists_once(client, monkeypatch):
    learner = client.post("/api/students", json={"name": "Quiz learner"}).json()["student_id"]
    response = client.post("/api/assessment/quiz", json={"student_id": learner,
        "topic_id": "recursion_call_stack", "question_count": 3})
    assert response.status_code == 200, response.text
    quiz = response.json()
    body = {"student_id": learner, "topic_id": "recursion_call_stack", "quiz_id": quiz["quiz_id"],
            "answers": [{"question_id": question["question_id"], "selected_option_index": 0}
                        for question in quiz["questions"]]}
    assert client.post("/api/assessment/submit", json={**body, "answers": body["answers"][:1]}).status_code == 422
    first = client.post("/api/assessment/submit", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["score_percentage"] == 100
    monkeypatch.setattr(student_service, "_student_service_instance", None)
    again = client.post("/api/assessment/submit", json=body)
    assert again.json() == first.json()
    profile = client.get(f"/api/students/{learner}").json()
    assert len(profile["quiz_history"]) == 1
    assert profile["current_difficulty"] == "Medium"


def test_bad_uploads_do_not_enter_library(client):
    learner = client.post("/api/students", json={"name": "Upload learner"}).json()["student_id"]
    assert client.post("/api/students", json={"name": "Blocked"},
                       headers={"Origin": "https://example.com"}).status_code == 403
    for filename, contents in [("empty.txt", b""), ("image.png", b"image"), ("scan.pdf", b"not a pdf")]:
        response = client.post("/api/materials", data={"student_id": learner}, files={"file": (filename, contents)})
        assert response.status_code == 422
    too_long = client.post("/api/materials", data={"student_id": learner},
                           files={"file": ("huge.txt", b"word " * 68000)})
    assert too_long.status_code == 422
    assert client.get("/api/materials", params={"student_id": learner}).json() == []


def test_text_pdf_keeps_page_citation(client):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
        DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 50 750 Td (A recursive function needs a base case.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf = BytesIO()
    writer.write(pdf)

    learner = client.post("/api/students", json={"name": "PDF learner"}).json()["student_id"]
    uploaded = client.post("/api/materials", data={"student_id": learner},
                           files={"file": ("lesson.pdf", pdf.getvalue(), "application/pdf")})
    assert uploaded.status_code == 201, uploaded.text
    response = client.post("/api/explanation/generate", json={"student_id": learner,
        "topic_id": uploaded.json()["id"]})
    assert response.status_code == 200, response.text
    assert response.json()["citations"][0]["page"] == 1

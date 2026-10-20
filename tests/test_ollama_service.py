import httpx
import pytest
from fastapi import HTTPException

from src.backend.schemas import Citation
from src.backend.services import ollama_service


def test_ollama_unavailable_is_actionable(monkeypatch):
    def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(ollama_service.httpx, "post", offline)
    with pytest.raises(HTTPException) as error:
        ollama_service.explain("Recursion", "Easy", [Citation(
            chunk_id="one", section_id="1", topic_name="Recursion", title="Notes",
            snippet="A base case terminates recursion.", similarity_score=0.9)], None)
    assert error.value.status_code == 503
    assert "Ollama" in error.value.detail


def test_quiz_rejects_unknown_source(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": '{"questions":[{"prompt":"What ends recursion?",'
                '"options":["Base case","Loop","Variable","Array"],"correct_option_index":0,'
                '"explanation":"A base case ends it.","misconception_diagnoses":{},'
                '"source_chunk_id":"other"}]}'}}
    monkeypatch.setattr(ollama_service.httpx, "post", lambda *args, **kwargs: Response())
    with pytest.raises(HTTPException) as error:
        ollama_service.questions("Recursion", "Easy", [Citation(
            chunk_id="one", section_id="1", topic_name="Recursion", title="Notes",
            snippet="A base case terminates recursion.", similarity_score=0.9)], 1)
    assert error.value.status_code == 502

import pytest
from src.backend.rag.chunker import load_all_syllabus_chunks
from src.backend.rag.qdrant_store import QdrantSyllabusStore

def test_load_all_syllabus_chunks():
    chunks = load_all_syllabus_chunks()
    assert len(chunks) >= 10, f"Expected at least 10 chunks, got {len(chunks)}"
    first = chunks[0]
    assert first.chunk_id.startswith("CHK-")
    assert first.topic_id != ""
    assert len(first.content) > 50

def test_qdrant_in_memory_indexing_and_search():
    store = QdrantSyllabusStore(in_memory=True)
    indexed_count = store.index_all_syllabus_chunks()
    assert indexed_count >= 10

    # Test semantic query for recursion
    query = "How do base cases stop call stack overflow in recursive functions?"
    results = store.search_syllabus(query=query, limit=3)
    assert len(results) > 0
    top_result = results[0]
    assert "recursion" in top_result.topic_name.lower() or "stack" in top_result.title.lower()
    assert top_result.similarity_score > 0.5
    assert top_result.chunk_id.startswith("CHK-")

def test_qdrant_topic_filtered_search():
    store = QdrantSyllabusStore(in_memory=True)
    store.index_all_syllabus_chunks()

    results = store.search_syllabus(
        query="memoization and overlapping subproblems",
        topic_id="dynamic_programming",
        limit=2
    )
    assert len(results) > 0
    for citation in results:
        assert "dynamic" in citation.topic_name.lower()

def test_get_all_chunks_scroll():
    store = QdrantSyllabusStore(in_memory=True)
    store.index_all_syllabus_chunks()
    chunks = store.get_all_chunks()
    assert len(chunks) >= 10
    topics = set(c.topic_id for c in chunks)
    assert "recursion_call_stack" in topics
    assert "binary_search_trees" in topics

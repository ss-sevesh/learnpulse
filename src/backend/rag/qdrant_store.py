import logging
from uuid import uuid4
from typing import List, Optional
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models
from fastembed import TextEmbedding

from src.backend.config import settings
from src.backend.schemas import SyllabusChunk, Citation
from src.backend.rag.chunker import load_all_syllabus_chunks

logger = logging.getLogger(__name__)

class QdrantSyllabusStore:
    def __init__(self, in_memory: bool = False):
        self.collection_name = settings.qdrant_collection_name
        self.embedding_dimension = settings.embedding_dimension

        # Initialize embedding model (BAAI/bge-small-en-v1.5)
        self.embed_model = TextEmbedding(model_name=settings.embedding_model_name)

        # Initialize Qdrant Client
        if in_memory:
            self.client = QdrantClient(":memory:")
            logger.info("Initialized in-memory Qdrant instance")
        else:
            Path(settings.qdrant_storage_path).mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=settings.qdrant_storage_path)
            logger.info(f"Initialized local Qdrant instance at {settings.qdrant_storage_path}")

        self._ensure_collection()

    def _ensure_collection(self, force_recreate: bool = False):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists and force_recreate:
            self.client.delete_collection(self.collection_name)
            exists = False

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest_models.VectorParams(
                    size=self.embedding_dimension,
                    distance=rest_models.Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection '{self.collection_name}' with dimension {self.embedding_dimension}")
            self.index_all_syllabus_chunks()

    def index_all_syllabus_chunks(self) -> int:
        chunks = load_all_syllabus_chunks()
        if not chunks:
            logger.warning("No syllabus chunks found to index into Qdrant.")
            return 0

        # Create full texts for embeddings combining title and content
        texts_to_embed = [f"{c.topic_name} - {c.title}: {c.content}" for c in chunks]
        embeddings = list(self.embed_model.embed(texts_to_embed))

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            point = rest_models.PointStruct(
                id=idx + 1,
                vector=vector.tolist(),
                payload={
                    "chunk_id": chunk.chunk_id,
                    "section_id": chunk.section_id,
                    "topic_id": chunk.topic_id,
                    "topic_name": chunk.topic_name,
                    "title": chunk.title,
                    "content": chunk.content,
                    "bloom_level": chunk.bloom_level,
                    "grade_level": chunk.grade_level
                }
            )
            points.append(point)

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Successfully indexed {len(points)} syllabus chunks into Qdrant '{self.collection_name}'.")
        return len(points)

    def search_syllabus(self, query: str, topic_id: Optional[str] = None, limit: int = 3, profile_id: Optional[str] = None) -> List[Citation]:
        query_embedding = list(self.embed_model.embed([query]))[0].tolist()

        query_filter = None
        if topic_id:
            conditions = [rest_models.FieldCondition(key="topic_id", match=rest_models.MatchValue(value=topic_id))]
            if profile_id:
                conditions.append(rest_models.FieldCondition(key="profile_id", match=rest_models.MatchValue(value=profile_id)))
            query_filter = rest_models.Filter(
                must=conditions
            )

        # Support both modern query_points (v1.11+) and legacy search
        if hasattr(self.client, "query_points"):
            res = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit
            )
            search_results = res.points
        else:
            search_results = getattr(self.client, "search")(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit
            )

        citations: List[Citation] = []
        for hit in search_results:
            payload = hit.payload or {}
            content = payload.get("content", "")
            snippet = content[:1200] + ("..." if len(content) > 1200 else "")

            citation = Citation(
                chunk_id=payload.get("chunk_id", "CHK-UNKNOWN"),
                section_id=payload.get("section_id", "SEC"),
                topic_name=payload.get("topic_name", "Curriculum Topic"),
                title=payload.get("title", "Curriculum Section"),
                snippet=snippet,
                similarity_score=round(float(hit.score), 4),
                document_id=payload.get("document_id"),
                page=payload.get("page")
            )
            citations.append(citation)

        return citations

    def index_material(self, document_id: str, profile_id: str, title: str, chunks: list[tuple[int | None, str]]):
        vectors = list(self.embed_model.embed([f"{title}: {content}" for _, content in chunks]))
        points = [rest_models.PointStruct(
            id=str(uuid4()), vector=vector.tolist(),
            payload={"chunk_id": f"{document_id}-{index}", "section_id": f"Page {page}" if page else "Text",
                     "topic_id": document_id, "topic_name": title, "title": title,
                     "content": content, "profile_id": profile_id,
                     "document_id": document_id, "page": page,
                     "bloom_level": "", "grade_level": ""}
        ) for index, ((page, content), vector) in enumerate(zip(chunks, vectors), 1)]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def delete_material(self, document_id: str):
        self.client.delete(collection_name=self.collection_name, points_selector=rest_models.FilterSelector(
            filter=rest_models.Filter(must=[rest_models.FieldCondition(
                key="document_id", match=rest_models.MatchValue(value=document_id))])))

    def get_all_chunks(self) -> List[SyllabusChunk]:
        """Returns all chunks stored in collection (up to 200)."""
        res = self.client.scroll(
            collection_name=self.collection_name,
            limit=200,
            with_payload=True,
            with_vectors=False
        )
        points, _ = res
        chunks: List[SyllabusChunk] = []
        for p in points:
            payload = p.payload or {}
            chunks.append(SyllabusChunk(
                chunk_id=payload.get("chunk_id", ""),
                section_id=payload.get("section_id", ""),
                topic_id=payload.get("topic_id", ""),
                topic_name=payload.get("topic_name", ""),
                title=payload.get("title", ""),
                content=payload.get("content", ""),
                bloom_level=payload.get("bloom_level", ""),
                grade_level=payload.get("grade_level", "")
            ))
        return chunks

# Global singleton instance for application use
_qdrant_store_instance: Optional[QdrantSyllabusStore] = None

def get_qdrant_store() -> QdrantSyllabusStore:
    global _qdrant_store_instance
    if _qdrant_store_instance is None:
        _qdrant_store_instance = QdrantSyllabusStore(in_memory=False)
    return _qdrant_store_instance

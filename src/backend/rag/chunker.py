import json
import logging
from pathlib import Path
from typing import List
from src.backend.config import SYLLABUS_DIR
from src.backend.schemas import SyllabusChunk

logger = logging.getLogger(__name__)

def load_syllabus_chunks_from_file(file_path: Path) -> List[SyllabusChunk]:
    chunks: List[SyllabusChunk] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        grade_level = data.get("grade_level", "Undergraduate")
        topics = data.get("topics", [])

        for topic in topics:
            topic_id = topic.get("topic_id", "general")
            topic_name = topic.get("name", "General Topic")
            bloom_level = topic.get("bloom_level", "Comprehension")

            for section in topic.get("reference_sections", []):
                sec_id = section.get("section_id", "SEC")
                title = section.get("title", "")
                content = section.get("content", "")

                chunk = SyllabusChunk(
                    chunk_id=f"CHK-{topic_id}-{sec_id}",
                    section_id=sec_id,
                    topic_id=topic_id,
                    topic_name=topic_name,
                    title=title,
                    content=content,
                    bloom_level=bloom_level,
                    grade_level=grade_level
                )
                chunks.append(chunk)

    except Exception as e:
        logger.error(f"Error loading syllabus file {file_path}: {e}")
        raise

    return chunks

def load_all_syllabus_chunks() -> List[SyllabusChunk]:
    all_chunks: List[SyllabusChunk] = []
    if not SYLLABUS_DIR.exists():
        logger.warning(f"Syllabus directory does not exist: {SYLLABUS_DIR}")
        return all_chunks

    for json_file in SYLLABUS_DIR.glob("*.json"):
        chunks = load_syllabus_chunks_from_file(json_file)
        all_chunks.extend(chunks)

    logger.info(f"Loaded {len(all_chunks)} syllabus chunks from {SYLLABUS_DIR}")
    return all_chunks

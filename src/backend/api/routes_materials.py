"""Local profile libraries: built-in topics and uploaded course material."""
import logging
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pypdf import PdfReader

from src.backend import storage
from src.backend.config import DATA_DIR
from src.backend.rag.chunker import load_all_syllabus_chunks
from src.backend.rag.qdrant_store import get_qdrant_store
from src.backend.services.material_service import get_material, require_profile

router = APIRouter(prefix="/api/materials", tags=["Materials"])
UPLOAD_DIR = DATA_DIR / "uploads"
MAX_BYTES = 10 * 1024 * 1024
MAX_CHUNKS = 300
logger = logging.getLogger(__name__)


def split_text(text: str):
    text = " ".join(text.split())
    return [text[start:start + 1200] for start in range(0, len(text), 1050) if text[start:start + 1200].strip()]


@router.get("")
def list_materials(student_id: str):
    require_profile(student_id)
    with storage.database() as db:
        return [{key: value for key, value in dict(row).items() if key != "path"} for row in db.execute(
            "SELECT * FROM materials WHERE profile_id = ? ORDER BY created_at DESC", (student_id,))]


@router.get("/topics")
def list_topics(student_id: str):
    require_profile(student_id)
    built_in = {chunk.topic_id: chunk.topic_name for chunk in load_all_syllabus_chunks()}
    topics = [{"topic_id": key, "title": value, "kind": "built_in"} for key, value in built_in.items()]
    topics.extend({"topic_id": item["id"], "title": item["title"], "kind": "upload",
                   "pages": item["pages"], "chunks": item["chunks"]} for item in list_materials(student_id))
    return topics


@router.post("", status_code=201)
def upload_material(student_id: str = Form(...), file: UploadFile = File(...)):
    require_profile(student_id)
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=422, detail="Upload a PDF, .txt, or .md file.")
    raw = file.file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Maximum file size is 10 MB.")
    if not raw:
        raise HTTPException(status_code=422, detail="The file is empty.")
    try:
        if suffix == ".pdf":
            reader = PdfReader(BytesIO(raw))
            if len(reader.pages) > 50:
                raise HTTPException(status_code=422, detail="PDFs may contain at most 50 pages.")
            pages = []
            for index, page in enumerate(reader.pages, 1):
                content = page.get_contents()
                if content and len(content.get_data()) > MAX_BYTES:
                    raise HTTPException(status_code=422, detail=f"Page {index} is too large to extract safely.")
                pages.extend((index, chunk) for chunk in split_text(page.extract_text() or ""))
            page_count = len(reader.pages)
        else:
            pages = [(None, chunk) for chunk in split_text(raw.decode("utf-8"))]
            page_count = 0
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not read this file as text.") from exc
    if not pages:
        raise HTTPException(status_code=422, detail="No selectable text found. Scanned PDFs need OCR before upload.")
    if len(pages) > MAX_CHUNKS:
        raise HTTPException(status_code=422, detail="This file contains too much text. Split it into smaller documents.")

    document_id = f"DOC-{uuid4().hex}"
    title = Path(filename).stem.strip()[:100] or "Untitled material"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{document_id}{suffix}"
    try:
        path.write_bytes(raw)
        get_qdrant_store().index_material(document_id, student_id, title, pages)
        with storage.database() as db:
            db.execute("INSERT INTO materials VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (document_id, student_id, title, filename, str(path), page_count,
                        len(pages), datetime.now(timezone.utc).isoformat()))
    except Exception:
        # shortcut: SQLite and Qdrant cannot commit together; add reconciliation if cleanup ever fails.
        try:
            get_qdrant_store().delete_material(document_id)
        except Exception:
            logger.exception("Could not remove indexed chunks for failed upload %s", document_id)
        path.unlink(missing_ok=True)
        raise
    return {"id": document_id, "title": title, "filename": filename,
            "pages": page_count, "chunks": len(pages)}


@router.delete("/{document_id}", status_code=204)
def delete_material(document_id: str, student_id: str):
    material = get_material(document_id, student_id)
    get_qdrant_store().delete_material(document_id)
    with storage.database() as db:
        db.execute("DELETE FROM materials WHERE id = ?", (document_id,))
    Path(material["path"]).unlink(missing_ok=True)

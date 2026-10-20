import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SYLLABUS_DIR = DATA_DIR / "syllabus"
STUDENTS_FILE = DATA_DIR / "synthetic_students.json"
QDRANT_STORAGE_PATH = DATA_DIR / "qdrant_db"

class Settings(BaseModel):
    app_name: str = "Personalised Learning & Assessment Generator"
    version: str = "2.0.0"
    debug: bool = True

    # Qdrant & Embedding Settings
    qdrant_collection_name: str = "curriculum_rag_store"
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    qdrant_storage_path: str = str(QDRANT_STORAGE_PATH)

    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M")

    # Adaptive Difficulty Engine Thresholds
    step_down_threshold: float = 60.0  # < 60% drops difficulty
    step_up_threshold: float = 80.0    # > 80% increases difficulty

settings = Settings()

"""Small persistent store for local learner profiles, materials, and quizzes."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from src.backend.config import DATA_DIR, STUDENTS_FILE
from src.backend.schemas import StudentProfile

DB_PATH = DATA_DIR / "learnpulse.sqlite3"


@contextmanager
def database():
    with sqlite3.connect(DB_PATH, timeout=30) as db:
        db.row_factory = sqlite3.Row
        yield db


def initialize():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with database() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY, data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS materials (
                id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, title TEXT NOT NULL,
                filename TEXT NOT NULL, path TEXT NOT NULL, pages INTEGER NOT NULL,
                chunks INTEGER NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
            CREATE TABLE IF NOT EXISTS quizzes (
                id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, topic_id TEXT NOT NULL,
                questions TEXT NOT NULL, result TEXT,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
        """)
        if db.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 0 and STUDENTS_FILE.exists():
            for raw in json.loads(STUDENTS_FILE.read_text(encoding="utf-8")).get("students", []):
                profile = StudentProfile.model_validate(raw)
                db.execute("INSERT INTO profiles VALUES (?, ?)", (profile.student_id, profile.model_dump_json()))


def list_profiles() -> list[StudentProfile]:
    with database() as db:
        return [StudentProfile.model_validate_json(row[0]) for row in db.execute("SELECT data FROM profiles ORDER BY id")]


def get_profile(profile_id: str) -> StudentProfile | None:
    with database() as db:
        row = db.execute("SELECT data FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return StudentProfile.model_validate_json(row[0]) if row else None


def save_profile(profile: StudentProfile):
    with database() as db:
        db.execute("INSERT OR REPLACE INTO profiles VALUES (?, ?)", (profile.student_id, profile.model_dump_json()))


def create_profile(name: str) -> StudentProfile:
    profile_id = f"LOCAL-{uuid4().hex[:10].upper()}"
    profile = StudentProfile(
        student_id=profile_id, name=name, roll_no=profile_id,
        grade_level="Local learner", target_track="Personal library",
        overall_mastery=0, current_difficulty="Easy", topic_mastery={},
        weak_topics=[], strong_topics=[], quiz_history=[]
    )
    save_profile(profile)
    return profile

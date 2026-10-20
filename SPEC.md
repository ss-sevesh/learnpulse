# Specification: local student learning console

## Objective and acceptance

Students can create/select local profiles, upload personal course material, study it with cited local AI explanations, take source-linked quizzes, and find their progress after restarting the app. The app has no teacher dashboard, Groq key flow, or simulated telemetry.

## Stack and commands

- Backend: FastAPI, Pydantic, SQLite standard library, Qdrant local storage, FastEmbed, Ollama HTTP API, pypdf.
- Frontend: React, TypeScript, Vite, CSS, lucide-react.
- Run: `python run.py`; backend tests: `pytest tests/ -q`; frontend checks: `cd frontend; npm run lint; npm run build`.

## Data and boundaries

- SQLite stores local profile JSON, upload metadata, full quiz answer keys, and one result per quiz. Bundled profiles seed an empty database once. The source JSON remains untouched.
- Every upload is assigned a random document ID. The original file lives under `data/uploads/`; extracted chunks live in Qdrant with its document and profile IDs. Deleting the upload removes its index entries, metadata, and file.
- PDF, UTF-8 text, and Markdown are accepted up to 10 MB and 300 indexed sections; PDFs are limited to 50 pages. Empty, invalid, and image-only files are rejected. Upload file names never become storage paths.
- Study and Practice resolve the selected topic and require ownership for uploads. Retrieval stays within that topic and profile; missing source text produces an error.
- Local profiles are not security identities. Bind the app to localhost; do not use it as a shared public service without authentication.

## API contracts

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET/POST | `/api/students` | List profiles / create a named profile |
| GET | `/api/students/{id}` | Profile, mastery, and history |
| GET | `/api/materials/topics?student_id=` | Built-in topics plus owned uploads |
| GET/POST | `/api/materials` | List owned uploads / multipart upload with `student_id` and `file` |
| DELETE | `/api/materials/{id}?student_id=` | Delete owned upload |
| POST | `/api/explanation/generate` | `student_id`, `topic_id`; structured answer, model name, citations |
| POST | `/api/assessment/quiz` | `student_id`, `topic_id`, `question_count`; public questions and citations |
| POST | `/api/assessment/submit` | Quiz ID, profile, topic, one answer per question; graded feedback and progress |
| GET | `/api/status` | Actual local model availability |

Ollama receives only retrieved source excerpts. Structured JSON output is validated before display or grading. Model/network failure returns an actionable 503; unusable output returns 502. Quiz submission checks ownership, completeness, answer indices, and current difficulty. Repeat submission returns the saved result without grading twice. Scores below 60% step down; scores of 80% or more step up; others retain the level. Topic mastery uses the existing 65% previous / 35% new score weighting.

## Tests

- Isolated API tests cover local profiles, owned uploads, cross-profile denial, invalid files, quiz validation, persistence, and repeat submission.
- Qdrant tests cover bundled indexing and topic-filtered search.
- Frontend lint/build and browser checks cover all four tabs, narrow layout, source display, and error states.

The four-tab technical explanation is also present in the root README and the application's disclosures.

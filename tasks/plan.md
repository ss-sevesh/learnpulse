# Implementation plan: student console

1. Specify the four-tab design and storage/API contracts in `design.md` and `SPEC.md`.
2. Persist demo and new profiles in SQLite; add profile-scoped upload extraction, indexing, listing, and deletion.
3. Replace Groq and deterministic response generation with schema-validated local Ollama explanation and quiz generation.
4. Persist generated quizzes and results; validate submission and update mastery once.
5. Replace the student/teacher dashboard interface with Library, Study, Practice, and Progress; remove unused components and routes.
6. Verify API boundaries, frontend build/lint, and real browser behavior, then update the README.

Dependency order: storage and materials → scoped retrieval → Ollama generation → grading → UI integration → verification.

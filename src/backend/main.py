import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings
from src.backend.rag.qdrant_store import get_qdrant_store
from src.backend.api.routes_students import router as students_router
from src.backend.api.routes_materials import router as materials_router
from src.backend.api.routes_explanation import router as explanation_router
from src.backend.api.routes_assessment import router as assessment_router
from src.backend.services.ollama_service import status as ollama_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Qdrant Vector Store and Syllabus Embeddings...")
    store = get_qdrant_store()
    logger.info(f"Qdrant Store ready. Collection: {store.collection_name}")
    yield
    logger.info("Shutting down backend services.")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Local student learning workspace with cited study and practice",
    lifespan=lifespan
)

# CORS Middleware for modern React frontend
LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def local_origin_only(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in LOCAL_ORIGINS:
        return JSONResponse(status_code=403, content={"detail": "This local API only accepts requests from LearnPulse."})
    return await call_next(request)

# Mount API Routers
app.include_router(students_router)
app.include_router(materials_router)
app.include_router(explanation_router)
app.include_router(assessment_router)

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "vector_store": "Local Qdrant",
        "llm_engine": "Ollama"
    }


@app.get("/api/status", tags=["System"])
def model_status():
    return ollama_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.backend.main:app", host="127.0.0.1", port=8000, reload=True)

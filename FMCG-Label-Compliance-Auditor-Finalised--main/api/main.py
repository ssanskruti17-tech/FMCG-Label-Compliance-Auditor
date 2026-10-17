from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routers import ocr, compliance, rag
from api.services.rag_service import init_rag_system, check_rag_health
from api.models.response_models import HealthResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize RAG on startup
    init_rag_system()
    yield
    # Cleanup on shutdown (if needed)
    pass

app = FastAPI(
    title="FMCG Label Compliance API",
    description="FastAPI wrapper for FSSAI compliance checks",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    rag_status = check_rag_health()
    return {
        "status": "ok",
        "ollama": rag_status,
        "chromadb": "connected" 
    }

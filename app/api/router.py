from fastapi import APIRouter

from app.api.routes.documents import router as documents_router
from app.api.routes.llm import router as llm_router
from app.api.routes.rag import router as rag_router

api_router = APIRouter()

api_router.include_router(
    llm_router,
    tags=["LLM"],
)

api_router.include_router(
    documents_router,
    prefix="/documents",
    tags=["Documents"],
)

api_router.include_router(
    rag_router,
    prefix="/rag",
    tags=["RAG"],
)

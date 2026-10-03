"""
Opella AI Decision Cockpit — Backend Application Entry Point
"""
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.providers import router as providers_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.data.local_warehouse import LocalWarehouseAdapter

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    configure_logging()
    logger.info(
        "opella_cockpit_starting",
        env=settings.APP_ENV,
        warehouse_adapter=settings.WAREHOUSE_ADAPTER,
    )
    # Pre-warm the local warehouse (loads demo data)
    adapter = LocalWarehouseAdapter.get_instance()
    await adapter.initialize()
    # Pre-warm knowledge store / RAG index
    try:
        from app.rag.vector_store import get_knowledge_store
        get_knowledge_store()
        logger.info("rag_knowledge_store_ready")
    except Exception as e:
        logger.warning("rag_knowledge_store_init_failed", error=str(e))
    logger.info("opella_cockpit_ready",
        warehouse=settings.WAREHOUSE_ADAPTER,
        llm_provider=settings.DEFAULT_LLM_PROVIDER,
    )
    yield
    logger.info("opella_cockpit_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Opella AI Decision Cockpit",
        version="0.1.0",
        description="Enterprise Multimodal AI & Data Engineering Platform",
        lifespan=lifespan,
        # Do not expose auto-generated docs in production
        docs_url="/api/docs" if settings.APP_ENV != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(providers_router, prefix="/api")

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "development",
    )

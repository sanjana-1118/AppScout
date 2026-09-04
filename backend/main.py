"""
backend/main.py
---------------
AppScout FastAPI Application Entrypoint.

Initializes the FastAPI application, configures CORS middleware, registers
domain routers, and exposes OpenAPI documentation at /docs and /redoc.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from experiment.db.database import check_connection
from backend.config import settings
from backend.routers import (
    overview_router,
    apps_router,
    categories_router,
    pricing_router,
    reviews_router,
    coverage_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    logger.info("Starting up %s v%s...", settings.PROJECT_NAME, settings.VERSION)
    is_connected, msg = check_connection()
    if is_connected:
        logger.info("[DB READY] %s", msg)
    else:
        logger.error("[DB ERROR] %s", msg)
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
def root():
    """Root entrypoint providing basic service metadata and documentation links."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "overview": f"{settings.API_V1_STR}/overview",
            "apps": f"{settings.API_V1_STR}/apps",
            "categories": f"{settings.API_V1_STR}/categories",
            "pricing": f"{settings.API_V1_STR}/pricing/overview",
            "reviews": f"{settings.API_V1_STR}/reviews",
            "coverage": f"{settings.API_V1_STR}/coverage",
            "health": f"{settings.API_V1_STR}/health",
        },
    }


# Register domain routers
app.include_router(overview_router, prefix=settings.API_V1_STR)
app.include_router(apps_router, prefix=settings.API_V1_STR)
app.include_router(categories_router, prefix=settings.API_V1_STR)
app.include_router(pricing_router, prefix=settings.API_V1_STR)
app.include_router(reviews_router, prefix=settings.API_V1_STR)
app.include_router(coverage_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)

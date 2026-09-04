"""
backend/routers/__init__.py
---------------------------
Export all routers for AppScout FastAPI backend.
"""

from .overview import router as overview_router
from .apps import router as apps_router
from .categories import router as categories_router
from .pricing import router as pricing_router
from .reviews import router as reviews_router
from .coverage import router as coverage_router

__all__ = [
    "overview_router",
    "apps_router",
    "categories_router",
    "pricing_router",
    "reviews_router",
    "coverage_router",
]

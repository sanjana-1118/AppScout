"""
backend/config.py
-----------------
Application settings and configuration for the AppScout FastAPI backend.
"""

from __future__ import annotations

import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    PROJECT_NAME: str = "AppScout API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Shopify App Market Intelligence Platform Backend API"
    API_V1_STR: str = "/api"
    
    # CORS Origins
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8000,*",
        ).split(",")
        if origin.strip()
    ]
    
    # Server settings
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()

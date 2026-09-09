"""
mcp_server/config.py
--------------------
Configuration settings and logging initialization for AppScout MCP server.
Ensures all logs strictly go to stderr so stdout remains dedicated to MCP stdio JSON-RPC.
"""

from __future__ import annotations

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

# Base URL for the existing AppScout FastAPI backend
APPSCOUT_API_BASE_URL: str = os.getenv("APPSCOUT_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# HTTP Client settings
REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("APPSCOUT_REQUEST_TIMEOUT", "30.0"))

# FastMCP Server settings
SERVER_NAME: str = "AppScout"
SERVER_VERSION: str = "1.0.0"

# Configure logging strictly to sys.stderr
logger = logging.getLogger("mcp_server")
logger.setLevel(logging.INFO)

if not logger.handlers:
    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] mcp_server: %(message)s",
        datefmt="%H:%M:%S",
    )
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)
    logger.propagate = False

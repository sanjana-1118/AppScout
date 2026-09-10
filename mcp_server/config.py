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

# Transport & Remote Deployment settings
# Default to stdio for local Antigravity pair-programming / CLI execution
MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0" if MCP_TRANSPORT in ("streamable-http", "sse") else "127.0.0.1")
# Render and other PaaS platforms inject PORT; fallback to MCP_PORT or 8000
MCP_PORT: int = int(os.getenv("PORT") or os.getenv("MCP_PORT", "8000"))

# Allowed hosts for DNS rebinding protection behind reverse proxies (e.g., Render)
# Format: comma-separated hostnames or '*' for permissive validation
ALLOWED_HOSTS_RAW: str = os.getenv("MCP_ALLOWED_HOSTS", "")
MCP_ALLOWED_HOSTS: list[str] = [h.strip() for h in ALLOWED_HOSTS_RAW.split(",") if h.strip()]

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

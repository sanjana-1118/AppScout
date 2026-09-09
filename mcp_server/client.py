"""
mcp_server/client.py
--------------------
Asynchronous HTTP client for interacting with the AppScout FastAPI backend.
Handles request lifecycle, timeouts, parameter sanitization, and structured error responses.
"""

from __future__ import annotations

from typing import Any
import httpx

from mcp_server.config import APPSCOUT_API_BASE_URL, REQUEST_TIMEOUT_SECONDS, logger


class AppScoutClient:
    """HTTP client communicating with the live AppScout FastAPI service."""

    def __init__(self, base_url: str = APPSCOUT_API_BASE_URL, timeout: float = REQUEST_TIMEOUT_SECONDS):
        self.base_url = base_url
        self.timeout = timeout

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a GET request against the FastAPI backend with error handling."""
        # Strip None values from params
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        url = f"{self.base_url}{path}"
        logger.debug("GET %s params=%s", url, clean_params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=clean_params)
                if response.status_code == 404:
                    detail = "Resource not found"
                    try:
                        detail = response.json().get("detail", detail)
                    except Exception:
                        pass
                    return {"error": "NotFound", "status_code": 404, "message": detail}

                response.raise_for_status()
                return response.json()

        except httpx.ConnectError:
            logger.error("Connection failed to AppScout backend at %s", self.base_url)
            return {
                "error": "BackendUnreachable",
                "message": f"AppScout backend is unreachable at {self.base_url}. Ensure the FastAPI server is running.",
            }
        except httpx.TimeoutException:
            logger.error("Request timed out after %ss for %s", self.timeout, url)
            return {
                "error": "Timeout",
                "message": f"Request to AppScout backend timed out after {self.timeout} seconds.",
            }
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error %s for %s: %s", exc.response.status_code, url, exc.response.text)
            return {
                "error": f"HTTP_{exc.response.status_code}",
                "status_code": exc.response.status_code,
                "message": exc.response.text,
            }
        except Exception as exc:
            logger.error("Unexpected error contacting AppScout backend: %s", exc)
            return {
                "error": "UnexpectedError",
                "message": f"An error occurred while communicating with the backend: {str(exc)}",
            }

    async def check_health(self) -> dict[str, Any]:
        """Call GET /api/health."""
        return await self._get("/api/health")

    async def get_overview(self) -> dict[str, Any]:
        """Call GET /api/overview."""
        return await self._get("/api/overview")

    async def list_apps(self, params: dict[str, Any]) -> dict[str, Any]:
        """Call GET /api/apps with filtering and pagination."""
        return await self._get("/api/apps", params=params)

    async def get_app_detail(self, slug_or_id: str) -> dict[str, Any]:
        """Call GET /api/apps/{slug_or_id}."""
        return await self._get(f"/api/apps/{slug_or_id}")

    async def list_categories(self, params: dict[str, Any]) -> dict[str, Any]:
        """Call GET /api/categories."""
        return await self._get("/api/categories", params=params)

    async def get_category_detail(self, slug_or_id: str, ranking_limit: int = 10) -> dict[str, Any]:
        """Call GET /api/categories/{slug_or_id}."""
        return await self._get(f"/api/categories/{slug_or_id}", params={"ranking_limit": ranking_limit})

    async def get_pricing_overview(self) -> dict[str, Any]:
        """Call GET /api/pricing/overview."""
        return await self._get("/api/pricing/overview")

    async def list_pricing_plans(self, params: dict[str, Any]) -> dict[str, Any]:
        """Call GET /api/pricing/plans."""
        return await self._get("/api/pricing/plans", params=params)

    async def list_reviews(self, params: dict[str, Any]) -> dict[str, Any]:
        """Call GET /api/reviews."""
        return await self._get("/api/reviews", params=params)

    async def get_review_stats(self) -> dict[str, Any]:
        """Call GET /api/reviews/stats."""
        return await self._get("/api/reviews/stats")

    async def get_coverage(self) -> dict[str, Any]:
        """Call GET /api/coverage."""
        return await self._get("/api/coverage")


# Default client instance
default_client = AppScoutClient()

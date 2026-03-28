"""
CORS configuration helper.

CORS is applied in ``app/main.py`` via FastAPI's built-in CORSMiddleware.
This module documents the settings and provides a helper to retrieve the
allowed origins list so it can be tested independently.
"""

from __future__ import annotations

from typing import List

from app.core.config import settings


def get_cors_origins() -> List[str]:
    """Return the list of allowed CORS origins from application settings.

    These are set via the CORS_ORIGINS environment variable (comma-separated).
    In development the default includes localhost:3000 and localhost:5173.
    In production, set CORS_ORIGINS to your frontend domain only.
    """
    return settings.cors_origins

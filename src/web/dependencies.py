"""Shared dependencies for RADAR API routers."""

import os
import secrets
import logging
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory, get_db

logger = logging.getLogger(__name__)

security = HTTPBasic()





# --- Auth ---

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Authenticate user via HTTP Basic Auth."""
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = os.environ.get("RADAR_USERNAME", "admin").encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )

    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = os.environ.get("RADAR_PASSWORD", "radar").encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

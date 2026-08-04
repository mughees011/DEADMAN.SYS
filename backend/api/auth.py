import os
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from werkzeug.security import check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

log = logging.getLogger(__name__)

# Secret key for signing the session cookie. In production, this should be set in .env
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-do-not-use-in-prod")
DASHBOARD_USER = os.environ.get("DASHBOARD_USER", "boss")
DASHBOARD_PASS_HASH = os.environ.get("DASHBOARD_PASS_HASH", "")

serializer = URLSafeTimedSerializer(SECRET_KEY)
COOKIE_NAME = "boss_session"

# We use HTTPBearer as a fallback/swagger UI convenience, but primarily rely on the cookie
bearer_scheme = HTTPBearer(auto_error=False)

def create_session_token() -> str:
    """Create a signed session token for the boss."""
    # Token valid for 30 days
    return serializer.dumps({"user": DASHBOARD_USER})

def verify_session_token(token: str) -> bool:
    try:
        data = serializer.loads(token, max_age=30 * 24 * 3600)
        return data.get("user") == DASHBOARD_USER
    except (SignatureExpired, BadSignature):
        return False

def verify_credentials(username: str, password: str) -> bool:
    if username != DASHBOARD_USER:
        return False
    if not DASHBOARD_PASS_HASH:
        log.warning("Authentication attempted but DASHBOARD_PASS_HASH is empty!")
        return False
    return check_password_hash(DASHBOARD_PASS_HASH, password)

async def get_current_user(
    request: Request,
    token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> str:
    """
    Dependency to authenticate the user via cookie or Bearer token.
    Raises 401 if unauthorized.
    """
    # 1. Check Cookie
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token and verify_session_token(cookie_token):
        return DASHBOARD_USER

    # 2. Check Bearer Token (for API scripts/curl)
    if token and verify_session_token(token.credentials):
        return DASHBOARD_USER

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

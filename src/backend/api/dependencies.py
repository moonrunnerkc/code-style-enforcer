# Author: Bradley R. Kinnard — gatekeepers

"""FastAPI dependencies for auth, rate limiting, request tracking."""

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, Request, status

from src.backend.config import settings
from src.backend.core.rate_limiter import is_allowed

log = logging.getLogger(__name__)


def _get_valid_keys() -> set[str]:
    """parse VALID_API_KEYS from settings. 'dev' means skip auth."""
    if settings.valid_api_keys == "dev":
        return set()  # empty = dev mode, allow all
    return set(k.strip() for k in settings.valid_api_keys.split(",") if k.strip())


async def get_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    api_key: str | None = Query(default=None, alias="api_key")
) -> str:
    """
    extract API key from Authorization header or query param.
    in dev mode (VALID_API_KEYS=dev), returns 'dev' without checking.
    """
    valid_keys = _get_valid_keys()

    # dev mode - skip auth entirely
    if not valid_keys:
        return "dev"

    # try header first: "Bearer <key>" or just "<key>"
    key = None
    if authorization:
        if authorization.startswith("Bearer "):
            key = authorization[7:]
        else:
            key = authorization

    # fall back to query param
    if not key:
        key = api_key

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing API key",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if key not in valid_keys:
        log.warning(f"invalid API key attempt: {key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid API key"
        )

    return key


async def check_rate_limit(
    request: Request,
    api_key: Annotated[str, Depends(get_api_key)]
) -> None:
    """check rate limit for this key. raises 429 if exceeded."""
    result = await is_allowed(api_key, limit=settings.rate_limit, window=settings.rate_window)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"rate limit exceeded, try again in {result.retry_after}s",
            headers={"Retry-After": str(result.retry_after)}
        )


# combine auth + rate limit into one dependency
async def require_auth(
    request: Request,
    api_key: Annotated[str, Depends(get_api_key)]
) -> str:
    """auth + rate limit in one shot"""
    await check_rate_limit(request, api_key)
    return api_key

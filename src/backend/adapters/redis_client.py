# Author: Bradley R. Kinnard — cache money

"""
Async redis connection. Single instance, lazy init, cleaned up in lifespan.
"""

import logging
from redis.asyncio import Redis

from src.backend.config import settings

log = logging.getLogger(__name__)

_redis: Redis | None = None


async def get_redis() -> Redis:
    """Get or create redis connection. Call once per request is fine, it's pooled."""
    global _redis
    if _redis is None:
        log.info(f"connecting to redis at {settings.redis_url}")
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Shut it down. Call from lifespan on app shutdown."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
        log.info("redis connection closed")


async def ping_redis() -> bool:
    """Health check. Returns False if redis is down or not connected."""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception as e:
        log.warning(f"redis ping failed: {e}")
        return False

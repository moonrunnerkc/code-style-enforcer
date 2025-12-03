# Author: Bradley R. Kinnard — save LLM calls or go broke

"""
Cache layer for AnalysisResult. Keyed by code_hash, stored as JSON in redis.
Default TTL is 7 days because code doesn't change that often.
"""

import logging

from src.backend.adapters.redis_client import get_redis
from src.backend.core.models import AnalysisResult

log = logging.getLogger(__name__)

CACHE_PREFIX = "analysis:"
DEFAULT_TTL = 604800  # 7 days


async def get_analysis(code_hash: str) -> AnalysisResult | None:
    """Fetch cached result by code_hash. Returns None on miss or error."""
    try:
        r = await get_redis()
        data = await r.get(f"{CACHE_PREFIX}{code_hash}")
        if data is None:
            return None
        return AnalysisResult.model_validate_json(data)
    except Exception as e:
        # don't crash if redis is down, just miss
        log.warning(f"cache get failed for {code_hash[:8]}: {e}")
        return None


async def set_analysis(code_hash: str, result: AnalysisResult, ttl: int = DEFAULT_TTL) -> bool:
    """Store result in cache. Returns True if successful."""
    try:
        r = await get_redis()
        data = result.model_dump_json()
        await r.set(f"{CACHE_PREFIX}{code_hash}", data, ex=ttl)
        return True
    except Exception as e:
        log.warning(f"cache set failed for {code_hash[:8]}: {e}")
        return False


async def delete_analysis(code_hash: str) -> bool:
    """Remove from cache. For testing or invalidation."""
    try:
        r = await get_redis()
        await r.delete(f"{CACHE_PREFIX}{code_hash}")
        return True
    except Exception as e:
        log.warning(f"cache delete failed for {code_hash[:8]}: {e}")
        return False

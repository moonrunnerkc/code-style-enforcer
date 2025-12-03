# Author: Bradley R. Kinnard — the bouncer

"""Redis-backed rate limiter. Protects the LLM bill from abuse."""

import logging

from src.backend.adapters.redis_client import get_redis

log = logging.getLogger(__name__)

# lua script for atomic incr + expire
# returns [count, ttl] - count is how many requests so far, ttl is seconds until reset
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end

local ttl = redis.call('TTL', key)
return {current, ttl}
"""


class RateLimitResult:
    """what happened when we checked the limit"""
    def __init__(self, allowed: bool, count: int, retry_after: int = 0):
        self.allowed = allowed
        self.count = count
        self.retry_after = retry_after  # seconds until window resets


async def is_allowed(key: str, limit: int = 10, window: int = 60) -> RateLimitResult:
    """
    check if key has capacity left. uses redis INCR + EXPIRE atomically.
    key should be like "rl:{ip}" or "rl:{api_key}"
    """
    redis = await get_redis()
    if redis is None:
        # redis down = fail open (allow request but log it)
        log.warning("redis unavailable, allowing request")
        return RateLimitResult(allowed=True, count=0)

    try:
        prefixed_key = f"rl:{key}"
        result = await redis.eval(RATE_LIMIT_SCRIPT, 1, prefixed_key, limit, window)
        count, ttl = int(result[0]), int(result[1])

        if count > limit:
            log.info(f"rate limit hit for {key}: {count}/{limit}, retry in {ttl}s")
            return RateLimitResult(allowed=False, count=count, retry_after=ttl)

        return RateLimitResult(allowed=True, count=count)

    except Exception as e:
        log.error(f"rate limit check failed: {e}")
        # fail open on errors
        return RateLimitResult(allowed=True, count=0)

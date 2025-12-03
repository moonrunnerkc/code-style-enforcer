# Author: Bradley R. Kinnard — where agent reputations live and die

"""DynamoDB weight storage with Redis fallback for local dev (shared across processes)."""

import json
import logging
import os
from decimal import Decimal
from typing import Literal

import aioboto3
from botocore.config import Config

from src.backend.config import settings
from src.backend.adapters.redis_client import get_redis

log = logging.getLogger(__name__)

AgentName = Literal["style", "naming", "minimalism", "docstring", "security"]
AGENTS: list[AgentName] = ["style", "naming", "minimalism", "docstring", "security"]

DEFAULT_WEIGHT = 1.0
MIN_WEIGHT, MAX_WEIGHT = 0.1, 2.0
TABLE_NAME = "AgentPreferences"
REDIS_WEIGHTS_KEY = "agent_weights"

# Redis for local dev (shared across processes, unlike in-memory dict)
USE_MEMORY = os.getenv("USE_LOCAL_DYNAMO", "").lower() in ("true", "1", "yes")

_session: aioboto3.Session | None = None


def _get_session() -> aioboto3.Session:
    global _session
    if _session is None:
        _session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id or "test",
            aws_secret_access_key=settings.aws_secret_access_key or "test",
            region_name=settings.aws_region
        )
    return _session


def _dynamo_kwargs() -> dict:
    """build kwargs for dynamo client, including local endpoint if set"""
    kwargs: dict = {"config": Config(connect_timeout=2, read_timeout=2)}
    if settings.dynamodb_endpoint:
        kwargs["endpoint_url"] = settings.dynamodb_endpoint
    return kwargs


async def get_weights(user_id: str = "global") -> dict[str, float]:
    """grab from dynamo (or Redis in dev), fall back to defaults if it's down"""
    # Redis mode for local dev (shared across processes)
    if USE_MEMORY:
        redis = await get_redis()
        key = f"{REDIS_WEIGHTS_KEY}:{user_id}"
        raw = await redis.get(key)
        if raw:
            return json.loads(raw)
        # initialize defaults
        defaults = {a: DEFAULT_WEIGHT for a in AGENTS}
        await redis.set(key, json.dumps(defaults))
        return defaults

    try:
        session = _get_session()
        async with session.resource("dynamodb", **_dynamo_kwargs()) as dynamo:
            table = await dynamo.Table(TABLE_NAME)
            resp = await table.get_item(Key={"user_id": user_id})
            if "Item" not in resp:
                return {a: DEFAULT_WEIGHT for a in AGENTS}
            item = resp["Item"]
            return {a: float(item.get(a, DEFAULT_WEIGHT)) for a in AGENTS}
    except Exception as e:
        log.warning(f"dynamo get_weights failed, using defaults: {e}")
        return {a: DEFAULT_WEIGHT for a in AGENTS}


async def update_weight(agent: str, delta: float, user_id: str = "global") -> float:
    """add delta, clamp, save. returns new value even if write fails"""
    weights = await get_weights(user_id)
    old = weights.get(agent, DEFAULT_WEIGHT)
    new = max(MIN_WEIGHT, min(MAX_WEIGHT, old + delta))

    # Redis mode for local dev
    if USE_MEMORY:
        redis = await get_redis()
        key = f"{REDIS_WEIGHTS_KEY}:{user_id}"
        weights[agent] = new
        await redis.set(key, json.dumps(weights))
        log.info(f"[redis] updated {agent} weight: {old:.3f} -> {new:.3f} (delta={delta:+.3f})")
        return new

    try:
        session = _get_session()
        async with session.resource("dynamodb", **_dynamo_kwargs()) as dynamo:
            table = await dynamo.Table(TABLE_NAME)
            # dynamo throws a fit if you give it floats
            item = {"user_id": user_id, **{a: Decimal(str(weights[a])) for a in AGENTS}}
            item[agent] = Decimal(str(new))
            await table.put_item(Item=item)
            log.info(f"updated {agent} weight: {old:.3f} -> {new:.3f} (delta={delta:+.3f})")
    except Exception as e:
        log.error(f"dynamo update_weight failed: {e}")
    return new


# mostly for tests
async def reset_weights(user_id: str = "global") -> dict[str, float]:
    defaults = {a: DEFAULT_WEIGHT for a in AGENTS}

    if USE_MEMORY:
        redis = await get_redis()
        key = f"{REDIS_WEIGHTS_KEY}:{user_id}"
        await redis.set(key, json.dumps(defaults))
        return defaults

    try:
        session = _get_session()
        async with session.resource("dynamodb", **_dynamo_kwargs()) as dynamo:
            table = await dynamo.Table(TABLE_NAME)
            item = {"user_id": user_id, **{a: Decimal(str(v)) for a, v in defaults.items()}}
            await table.put_item(Item=item)
    except Exception as e:
        log.warning(f"dynamo reset failed: {e}")
    return defaults

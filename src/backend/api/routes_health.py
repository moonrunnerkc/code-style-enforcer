# Author: Bradley R. Kinnard — the app's pulse check

"""Health endpoint with actual connectivity checks. Also /metrics."""

import logging
import subprocess

from fastapi import APIRouter, Request, Response

from src.backend.adapters.metrics_client import get_metrics
from src.backend.adapters.redis_client import get_redis
from src.backend.config import settings

router = APIRouter(tags=["health"])
log = logging.getLogger(__name__)


def _git_sha() -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=1, check=False
        )
        return r.stdout.strip() or None
    except Exception:
        return None


async def _check_redis() -> str:
    """ping redis, return ok or error message"""
    try:
        redis = await get_redis()
        await redis.ping()
        return "ok"
    except Exception as e:
        return f"error: {e}"


async def _check_dynamodb() -> str:
    """try to list tables, return ok or error. skipped if no endpoint configured and no AWS creds."""
    # skip in local dev if no endpoint and no real creds
    if not settings.dynamodb_endpoint and not settings.aws_access_key_id:
        return "skipped"
    try:
        import aioboto3
        from botocore.config import Config
        session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id or "test",
            aws_secret_access_key=settings.aws_secret_access_key or "test",
            region_name=settings.aws_region
        )
        kwargs: dict = {"config": Config(connect_timeout=2, read_timeout=2)}
        if settings.dynamodb_endpoint:
            kwargs["endpoint_url"] = settings.dynamodb_endpoint
        async with session.client("dynamodb", **kwargs) as dynamo:
            await dynamo.list_tables(Limit=1)
            return "ok"
    except Exception as e:
        return f"error: {e}"


async def _check_sqs() -> str:
    """try to list queues, return ok or error. skipped if no endpoint configured and no AWS creds."""
    if not settings.sqs_endpoint and not settings.aws_access_key_id:
        return "skipped"
    try:
        import aioboto3
        from botocore.config import Config
        session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id or "test",
            aws_secret_access_key=settings.aws_secret_access_key or "test",
            region_name=settings.aws_region
        )
        kwargs: dict = {"config": Config(connect_timeout=2, read_timeout=2)}
        if settings.sqs_endpoint:
            kwargs["endpoint_url"] = settings.sqs_endpoint
        async with session.client("sqs", **kwargs) as sqs:
            await sqs.list_queues(MaxResults=1)
            return "ok"
    except Exception as e:
        return f"error: {e}"


@router.get("/health")
async def health_check(request: Request) -> dict:
    """full health check with redis/dynamo/sqs status"""
    rid = getattr(request.state, "request_id", "unknown")
    sha = _git_sha()

    redis_status = await _check_redis()
    dynamo_status = await _check_dynamodb()
    sqs_status = await _check_sqs()

    # ok or skipped counts as healthy
    all_ok = all(s in ("ok", "skipped") for s in [redis_status, dynamo_status, sqs_status])

    log.info(f"health | redis={redis_status} dynamo={dynamo_status} sqs={sqs_status}")

    return {
        "status": "ok" if all_ok else "degraded",
        "request_id": rid,
        "git_sha": sha,
        "redis": redis_status,
        "dynamodb": dynamo_status,
        "sqs": sqs_status
    }


@router.get("/metrics")
async def metrics() -> Response:
    """prometheus metrics endpoint"""
    return Response(content=get_metrics(), media_type="text/plain; charset=utf-8")

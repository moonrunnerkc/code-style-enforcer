# Author: Bradley R. Kinnard — queue it up

"""SQS client with Redis fallback for local dev (shared across processes)."""

import asyncio
import json
import logging
import os
import uuid
from typing import Any

import aioboto3
from botocore.config import Config

from src.backend.config import settings
from src.backend.adapters.redis_client import get_redis

log = logging.getLogger(__name__)

# Redis queue for local dev (shared across processes, unlike in-memory deque)
REDIS_QUEUE_KEY = "feedback_queue"
USE_MEMORY = os.getenv("USE_LOCAL_SQS", "").lower() in ("true", "1", "yes")

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


def _sqs_kwargs() -> dict:
    kwargs: dict = {"config": Config(connect_timeout=2, read_timeout=5)}
    if settings.sqs_endpoint:
        kwargs["endpoint_url"] = settings.sqs_endpoint
    return kwargs


async def send_message(message: dict[str, Any]) -> str:
    """send to SQS (or Redis queue in dev). returns message id"""
    if USE_MEMORY:
        # use Redis list as queue (shared across processes)
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        payload = json.dumps({"id": msg_id, "body": message})
        redis = await get_redis()
        await redis.lpush(REDIS_QUEUE_KEY, payload)
        depth = await redis.llen(REDIS_QUEUE_KEY)
        log.info(f"[redis] queued message {msg_id}, queue depth: {depth}")
        return msg_id

    try:
        session = _get_session()
        async with session.client("sqs", **_sqs_kwargs()) as sqs:
            resp = await sqs.send_message(
                QueueUrl=settings.sqs_queue_url,
                MessageBody=json.dumps(message)
            )
            msg_id = resp.get("MessageId", "unknown")
            log.info(f"queued message {msg_id}")
            return msg_id
    except Exception as e:
        log.error(f"SQS send failed: {e}")
        raise


async def receive_messages(max_messages: int = 10, wait_seconds: int = 20) -> list[dict]:
    """receive from SQS (or Redis queue in dev). returns list of messages"""
    if USE_MEMORY:
        # use Redis list as queue
        redis = await get_redis()
        messages = []
        for _ in range(max_messages):
            raw = await redis.rpop(REDIS_QUEUE_KEY)
            if not raw:
                break
            msg = json.loads(raw)
            messages.append({
                "MessageId": msg["id"],
                "Body": json.dumps(msg["body"]),
                "ReceiptHandle": msg["id"]
            })
        if not messages:
            # simulate long poll with shorter wait
            await asyncio.sleep(min(wait_seconds, 2))
        return messages

    try:
        session = _get_session()
        async with session.client("sqs", **_sqs_kwargs()) as sqs:
            resp = await sqs.receive_message(
                QueueUrl=settings.sqs_queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_seconds
            )
            return resp.get("Messages", [])
    except Exception as e:
        log.error(f"SQS receive failed: {e}")
        return []


async def delete_message(receipt_handle: str) -> None:
    """delete processed message from SQS (no-op in Redis mode, already popped)"""
    if USE_MEMORY:
        log.debug(f"[redis] deleted message {receipt_handle}")
        return

    try:
        session = _get_session()
        async with session.client("sqs", **_sqs_kwargs()) as sqs:
            await sqs.delete_message(
                QueueUrl=settings.sqs_queue_url,
                ReceiptHandle=receipt_handle
            )
    except Exception as e:
        log.error(f"SQS delete failed: {e}")


async def queue_depth() -> int:
    """return current queue depth"""
    if USE_MEMORY:
        redis = await get_redis()
        return await redis.llen(REDIS_QUEUE_KEY)
    return -1  # unknown for real SQS without extra call

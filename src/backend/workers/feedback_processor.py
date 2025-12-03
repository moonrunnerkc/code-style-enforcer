# Author: Bradley R. Kinnard — the night shift

"""
long-running worker that pulls feedback from SQS and updates agent weights.
run this as a separate process: python -m src.backend.workers.feedback_processor
"""

import asyncio
import json
import logging
import signal

from src.backend.adapters import sqs_client
from src.backend.rl.rl_trainer import apply_feedback
from src.backend.logging_config import setup_logging

log = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds between empty polls
MAX_MESSAGES = 10

_shutdown = False


def handle_signal(sig, frame):
    global _shutdown
    log.info(f"got signal {sig}, shutting down after current batch")
    _shutdown = True


async def process_message(msg: dict) -> bool:
    """parse and apply feedback. returns True if processed ok"""
    try:
        body = json.loads(msg["Body"])
        agent = body["agent"]
        accepted = body["accepted"]
        rating = body["user_rating"]

        await apply_feedback(agent, accepted, rating)
        return True
    except Exception as e:
        log.error(f"failed to process message: {e}")
        return False


async def run_worker():
    """poll SQS (or memory queue) forever, process messages, delete on success"""
    global _shutdown

    backoff = 1
    log.info(f"feedback processor starting (memory mode: {sqs_client.USE_MEMORY})")

    while not _shutdown:
        try:
            messages = await sqs_client.receive_messages(
                max_messages=MAX_MESSAGES,
                wait_seconds=20
            )

            if not messages:
                await asyncio.sleep(POLL_INTERVAL)
                backoff = 1
                continue

            log.info(f"got {len(messages)} messages")

            for msg in messages:
                ok = await process_message(msg)
                if ok:
                    await sqs_client.delete_message(msg["ReceiptHandle"])
                # if not ok, message returns to queue after visibility timeout

            backoff = 1

        except Exception as e:
            log.error(f"poll error: {e}, backing off {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    log.info("feedback processor stopped")


def main():
    setup_logging(level="INFO")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

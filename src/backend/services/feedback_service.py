# Author: Bradley R. Kinnard — fire and forget

"""push feedback to SQS (or memory queue), don't wait for RL. that's the worker's problem"""

import logging

from src.backend.adapters import sqs_client

log = logging.getLogger(__name__)


async def enqueue_feedback(
    analysis_id: str,
    suggestion_id: str,
    agent: str,
    accepted: bool,
    user_rating: int
) -> bool:
    """shove it in the queue, return True if it worked"""
    msg = {
        "analysis_id": analysis_id,
        "suggestion_id": suggestion_id,
        "agent": agent,
        "accepted": accepted,
        "user_rating": user_rating
    }
    try:
        msg_id = await sqs_client.send_message(msg)
        log.info(f"queued feedback for {agent} suggestion={suggestion_id[:8]} msg_id={msg_id}")
        return True
    except Exception as e:
        log.error(f"sqs enqueue failed: {e}")
        return False

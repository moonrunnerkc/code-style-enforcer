# Author: Bradley R. Kinnard — prove RL actually works

"""
Integration test: submit feedback, verify weights change.
Run with: pytest tests/integration/test_rl_feedback_flow.py -v
"""

import os
import pytest

# set env vars before imports
os.environ["USE_LOCAL_SQS"] = "true"
os.environ["USE_LOCAL_DYNAMO"] = "true"

from src.backend.rl.policy_store import get_weights, reset_weights
from src.backend.rl.rl_trainer import apply_feedback
from src.backend.services.feedback_service import enqueue_feedback
from src.backend.adapters import sqs_client
from src.backend.adapters import redis_client
from src.backend.workers.feedback_processor import process_message


@pytest.fixture(autouse=True)
async def reset_state():
    """reset weights and close redis between tests"""
    await reset_weights()
    yield
    await redis_client.close_redis()


@pytest.mark.asyncio
async def test_weights_start_at_one():
    """sanity check: all weights start at 1.0"""
    weights = await get_weights()
    for agent in ["style", "naming", "minimalism", "docstring", "security"]:
        assert weights[agent] == 1.0, f"{agent} should start at 1.0"


@pytest.mark.asyncio
async def test_reject_lowers_weight():
    """single reject should lower weight"""
    before = await get_weights()
    assert before["security"] == 1.0

    # apply single reject with rating 5
    await apply_feedback("security", accepted=False, user_rating=5)

    after = await get_weights()
    assert after["security"] < 1.0, "reject should lower weight"
    assert after["security"] == pytest.approx(0.75, abs=0.01)  # 1.0 - 0.05*5 = 0.75


@pytest.mark.asyncio
async def test_accept_raises_weight():
    """single accept should raise weight (if not already at max)"""
    # first lower it
    await apply_feedback("style", accepted=False, user_rating=5)
    lowered = await get_weights()
    assert lowered["style"] < 1.0

    # then accept to raise it
    await apply_feedback("style", accepted=True, user_rating=5)
    raised = await get_weights()
    assert raised["style"] > lowered["style"], "accept should raise weight"


@pytest.mark.asyncio
async def test_five_rejects_drops_below_90():
    """5 rejects with rating 5 should drop weight significantly"""
    for _ in range(5):
        await apply_feedback("security", accepted=False, user_rating=5)

    weights = await get_weights()
    # 1.0 - 5*(0.05*5) = 1.0 - 1.25 = -0.25 -> clamped to 0.1
    assert weights["security"] < 0.90, f"security weight should be < 0.90, got {weights['security']}"


@pytest.mark.asyncio
async def test_weights_clamp_at_min():
    """weight can't go below MIN_WEIGHT (0.1)"""
    for _ in range(50):  # way more than needed
        await apply_feedback("naming", accepted=False, user_rating=5)

    weights = await get_weights()
    assert weights["naming"] >= 0.1, "weight should clamp at 0.1"
    assert weights["naming"] == pytest.approx(0.1, abs=0.01)


@pytest.mark.asyncio
async def test_weights_clamp_at_max():
    """weight can't go above MAX_WEIGHT (2.0)"""
    for _ in range(50):  # way more than needed
        await apply_feedback("minimalism", accepted=True, user_rating=5)

    weights = await get_weights()
    assert weights["minimalism"] <= 2.0, "weight should clamp at 2.0"
    assert weights["minimalism"] == pytest.approx(2.0, abs=0.01)


@pytest.mark.asyncio
async def test_queue_and_process_message():
    """test the full queue flow: enqueue -> process -> weight changes"""
    before = await get_weights()
    assert before["docstring"] == 1.0

    # enqueue feedback
    await enqueue_feedback(
        analysis_id="test-123",
        suggestion_id="sug-456",
        agent="docstring",
        accepted=False,
        user_rating=5
    )

    # manually process the message (simulating worker)
    messages = await sqs_client.receive_messages(max_messages=1, wait_seconds=1)
    assert len(messages) == 1, "should have 1 message in queue"

    ok = await process_message(messages[0])
    assert ok, "message processing should succeed"

    after = await get_weights()
    assert after["docstring"] < 1.0, "weight should have dropped after processing"


@pytest.mark.asyncio
async def test_weights_persist_in_redis():
    """weights should persist across get_weights calls"""
    await apply_feedback("style", accepted=False, user_rating=3)

    w1 = await get_weights()
    w2 = await get_weights()

    assert w1["style"] == w2["style"], "weights should be consistent"
    assert w1["style"] < 1.0, "weight should have changed"

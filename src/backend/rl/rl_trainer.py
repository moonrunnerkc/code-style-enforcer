# Author: Bradley R. Kinnard — nudge weights based on user votes

"""apply reward to agent weight via EMA. alpha=0.05 so it takes ~20 feedbacks to shift significantly"""

import logging

from src.backend.rl.policy_store import update_weight
from src.backend.rl.reward_engine import compute_reward

log = logging.getLogger(__name__)

ALPHA = 0.05  # learning rate, kept small so trolls can't tank an agent in 3 clicks


async def apply_feedback(agent: str, accepted: bool, user_rating: int, user_id: str = "global") -> float:
    """
    compute reward, scale by alpha, bump the weight.
    returns the new weight value
    """
    reward = compute_reward(accepted, user_rating)
    delta = ALPHA * reward  # small nudge

    new_weight = await update_weight(agent, delta, user_id)
    log.info(f"rl update: {agent} reward={reward:+.1f} delta={delta:+.3f} new_weight={new_weight:.3f}")
    return new_weight

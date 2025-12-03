# Author: Bradley R. Kinnard — show me the weights

"""Agent weights endpoint. Reveals who's winning the RL game."""

from fastapi import APIRouter

from src.backend.rl.policy_store import get_weights

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/weights")
async def weights():
    """Current agent weights. Higher = more influence on final suggestions."""
    return await get_weights()

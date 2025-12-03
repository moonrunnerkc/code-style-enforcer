# Author: Bradley R. Kinnard — turn stars into numbers

"""feedback to reward. accepted = positive, rejected = negative."""

from typing import Literal

AgentName = Literal["style", "naming", "minimalism", "docstring", "security"]


def compute_reward(accepted: bool, user_rating: int) -> float:
    """
    simple: accept = +rating, reject = -rating
    rating is 1-5, so reward range is [-5, +5]
    """
    if accepted:
        return float(user_rating)
    return float(-user_rating)

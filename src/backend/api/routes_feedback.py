# Author: Bradley R. Kinnard — your opinion matters (eventually)

"""POST /feedback - queue it and get out fast"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.backend.api.dependencies import require_auth
from src.backend.api.schemas import FeedbackRequest, FeedbackResponse
from src.backend.services.feedback_service import enqueue_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])
log = logging.getLogger(__name__)


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    api_key: Annotated[str, Depends(require_auth)]
) -> FeedbackResponse:
    """queue feedback for async RL processing. returns immediately."""
    request_id = getattr(request.state, "request_id", "unknown")

    ok = await enqueue_feedback(
        analysis_id=body.analysis_id,
        suggestion_id=body.suggestion_id,
        agent=body.agent,
        accepted=body.accepted,
        user_rating=body.user_rating
    )

    if ok:
        return FeedbackResponse(status="queued", message="feedback received", request_id=request_id)

    log.warning("sqs failed, feedback dropped")
    return FeedbackResponse(status="error", message="queue unavailable", request_id=request_id)

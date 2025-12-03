# Author: Bradley R. Kinnard — where code goes to be judged

"""POST /analyze endpoint. Validate, analyze, return."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.backend.api.dependencies import require_auth
from src.backend.api.schemas import AnalyzeRequest, AnalysisResult
from src.backend.services.analyzer_service import analyze
from src.backend.utils.validation import validate_analyze_request

router = APIRouter(prefix="/analyze", tags=["analyze"])
log = logging.getLogger(__name__)


@router.post("", response_model=AnalysisResult)
async def analyze_code(
    request: Request,
    body: AnalyzeRequest,
    api_key: Annotated[str, Depends(require_auth)]
) -> AnalysisResult:
    """run all agents, return merged suggestions. auth + rate limited."""
    request_id = getattr(request.state, "request_id", "unknown")

    validate_analyze_request(body.code, body.language, body.detail_level)

    log.info(f"analyze | key={api_key[:8]}... lang={body.language} len={len(body.code)}")

    result = await analyze(
        code=body.code,
        language=body.language,
        detail_level=body.detail_level,
        request_id=request_id
    )

    log.info(f"analyze done | id={result.analysis_id} cache={result.from_cache}")

    return result

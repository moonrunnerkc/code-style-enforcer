# Author: Bradley R. Kinnard — the orchestrator

"""
Main analysis pipeline. Hash, cache check, dispatch, merge, cache store.
One function to rule them all.
"""

import logging
import uuid

from src.backend.core.cache import get_analysis, set_analysis
from src.backend.core.code_hash import compute_code_hash
from src.backend.core.models import AnalysisResult
from src.backend.services.agent_dispatcher import dispatch
from src.backend.services.suggestion_merger import merge

log = logging.getLogger(__name__)

CACHE_TTL = 604800  # 7 days


async def analyze(code: str, language: str, detail_level: str, request_id: str) -> AnalysisResult:
    """
    Full analysis pipeline:
    1. hash the code
    2. check cache
    3. on hit: return cached result with from_cache=True
    4. on miss: run agents, merge, cache, return with from_cache=False
    """
    code_hash = compute_code_hash(code)
    analysis_id = f"an-{uuid.uuid4().hex[:12]}"

    # cache hit?
    cached = await get_analysis(code_hash)
    if cached is not None:
        log.info(f"cache hit for {code_hash[:8]}, returning cached result")
        # update the request_id and analysis_id for this request
        return AnalysisResult(
            analysis_id=analysis_id,
            code_hash=code_hash,
            from_cache=True,
            suggestions=cached.suggestions,
            agent_weights=cached.agent_weights,
            agent_results=cached.agent_results,
            request_id=request_id
        )

    # cache miss, do the work
    log.info(f"cache miss for {code_hash[:8]}, running agents")
    agent_results = await dispatch(code, language)

    result = await merge(
        agent_results=agent_results,
        analysis_id=analysis_id,
        code_hash=code_hash,
        request_id=request_id,
        from_cache=False
    )

    # store in cache for next time
    await set_analysis(code_hash, result, ttl=CACHE_TTL)
    log.info(f"cached {code_hash[:8]} with {len(result.suggestions)} suggestions")

    return result

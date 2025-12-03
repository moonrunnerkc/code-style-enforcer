# Author: Bradley R. Kinnard — deduplicate and promote the truth

"""Merge suggestions from all agents, dedupe, apply RL weights, sort by severity × confidence."""

import re
from src.backend.core.models import AgentResult, AnalysisResult, Suggestion
from src.backend.rl.policy_store import get_weights

# agent priority for tiebreaks: minimalism catches bugs, security is critical, rest are style
AGENT_PRIORITY = {"minimalism": 5, "security": 4, "naming": 3, "docstring": 2, "style": 1}


def _score_suggestion(s: Suggestion, weight: float) -> Suggestion:
    """
    Score = severity × confidence × agent_weight
    Severity 1-5, so normalize to 0.2-1.0 range for scoring.
    Critical (5) with conf 1.0 = score 1.0
    Hint (1) with conf 0.7 = score 0.14
    """
    severity_factor = s.severity / 5.0
    new_score = severity_factor * s.confidence * weight
    return Suggestion(
        id=s.id,
        agent=s.agent,
        type=s.type,
        message=s.message,
        severity=s.severity,
        confidence=s.confidence,
        score=round(new_score, 4)
    )


def _normalize_message(msg: str) -> str:
    """strip line numbers, punctuation, and noise for fuzzy matching"""
    normalized = re.sub(r'lines?\s*\d+(-\d+)?', '', msg.lower())
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return ' '.join(normalized.split())


def _get_dedup_key(s: Suggestion) -> str:
    """
    Generate a dedup key from the suggestion.
    Groups similar findings so we keep only the best one.
    """
    key = _normalize_message(s.message)

    # canonical keys for common issue patterns
    if any(w in key for w in ('duplicate', 'identical', 'twice', 'same arguments', 'called twice')):
        return 'duplicate_operation'
    if 'unused' in key and 'import' in key:
        return 'unused_import'
    if 'unused' in key and 'variable' in key:
        return 'unused_variable'
    if 'docstring' in key and ('missing' in key or 'no docstring' in key):
        return 'missing_docstring'

    return key


def _is_better(new: Suggestion, existing: Suggestion) -> bool:
    """
    True if new should replace existing.
    Highest severity wins. Tie: highest confidence. Tie: agent priority.
    """
    if new.severity != existing.severity:
        return new.severity > existing.severity
    if new.confidence != existing.confidence:
        return new.confidence > existing.confidence
    return AGENT_PRIORITY.get(new.agent, 0) > AGENT_PRIORITY.get(existing.agent, 0)


def _deduplicate(suggestions: list[Suggestion]) -> list[Suggestion]:
    """
    Group by normalized message, keep highest severity × confidence.
    Tiebreaker: minimalism > security > others.
    """
    seen: dict[str, Suggestion] = {}

    for s in suggestions:
        key = _get_dedup_key(s)
        if key not in seen or _is_better(s, seen[key]):
            seen[key] = s

    return list(seen.values())


async def merge(
    agent_results: list[AgentResult],
    analysis_id: str,
    code_hash: str,
    request_id: str,
    from_cache: bool = False
) -> AnalysisResult:
    """
    Pull fresh weights from dynamo, score suggestions by severity × confidence × weight.
    Deduplicate similar findings. Sort critical issues first.
    """
    weights = await get_weights()
    all_suggestions: list[Suggestion] = []

    for ar in agent_results:
        w = weights.get(ar.agent, 1.0)
        for s in ar.suggestions:
            all_suggestions.append(_score_suggestion(s, w))

    # dedupe before sorting
    deduped = _deduplicate(all_suggestions)

    # Primary sort: severity desc (criticals first)
    # Secondary sort: score desc (within same severity)
    deduped.sort(key=lambda x: (x.severity, x.score), reverse=True)

    return AnalysisResult(
        analysis_id=analysis_id,
        code_hash=code_hash,
        from_cache=from_cache,
        suggestions=deduped,
        agent_weights=weights,
        agent_results=agent_results,
        request_id=request_id
    )

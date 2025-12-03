# Author: Bradley R. Kinnard — the contract between client and server

"""
API schemas. Re-exports from models.py plus any API-specific wrappers.
Keep request/response definitions in one place for OpenAPI docs.
"""

from pydantic import BaseModel

# re-export the core models for API use
from src.backend.core.models import (
    AnalyzeRequest,
    AnalysisResult,
    FeedbackRequest,
    FeedbackResponse,
    AgentWeightsResponse,
    HealthResponse,
    Suggestion,
)

__all__ = [
    "AnalyzeRequest",
    "AnalysisResult",
    "FeedbackRequest",
    "FeedbackResponse",
    "AgentWeightsResponse",
    "HealthResponse",
    "Suggestion",
    "ErrorResponse",
    "ValidationErrorResponse",
]


class ErrorResponse(BaseModel):
    """Generic error for 4xx/5xx responses."""
    error: str
    detail: str | None = None
    request_id: str


class ValidationErrorDetail(BaseModel):
    loc: list[str]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    """422 response shape, matches FastAPI's default."""
    detail: list[ValidationErrorDetail]
    request_id: str | None = None

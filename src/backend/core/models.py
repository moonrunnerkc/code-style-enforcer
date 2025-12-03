# Author: Bradley R. Kinnard — where types go to be validated

"""
Pydantic models for the analysis pipeline and API responses.
Severity enum so we stop guessing what 3 means.
"""

from enum import IntEnum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Severity(IntEnum):
    """No magic numbers. Skip 4 because nothing is just 'error' without being critical."""
    HINT = 1
    INFO = 2
    WARNING = 3
    CRITICAL = 5  # intentionally skip 4, CRITICAL stands alone


class Suggestion(BaseModel):
    """One suggestion from one agent. Frozen so we don't accidentally mutate cached results."""
    model_config = ConfigDict(frozen=True)

    id: str
    agent: Literal["style", "naming", "minimalism", "docstring", "security"]
    type: str  # formatting, naming, complexity, etc
    message: str
    severity: int = Field(default=Severity.INFO, ge=1, le=5)  # use Severity enum values
    confidence: float = Field(ge=0.0, le=1.0)
    score: float = Field(default=0.0)  # after RL weighting, can exceed 1.0


class AgentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent: Literal["style", "naming", "minimalism", "docstring", "security"]
    suggestions: list[Suggestion]
    took_ms: int
    error: str | None = None  # timeout, crash, whatever


class AnalysisResult(BaseModel):
    """What /analyze returns. The suggestions list is already merged and scored."""
    analysis_id: str
    code_hash: str
    from_cache: bool
    suggestions: list[Suggestion]
    agent_weights: dict[str, float]
    agent_results: list[AgentResult] | None = None  # include raw output if client wants it
    request_id: str


class HealthResponse(BaseModel):
    """Basic pulse check. The redis/dynamo/sqs/llm fields stay None until we wire those up."""
    status: Literal["ok", "degraded", "down"]
    request_id: str
    git_sha: str | None = None
    redis: Literal["ok", "down"] | None = None
    dynamodb: Literal["ok", "down"] | None = None
    sqs: Literal["ok", "down"] | None = None
    llm: Literal["ok", "down"] | None = None


# request/response models

class AnalyzeRequest(BaseModel):
    language: str
    code: str
    detail_level: Literal["fast", "normal", "deep"] = "normal"


class FeedbackRequest(BaseModel):
    analysis_id: str
    suggestion_id: str
    agent: Literal["style", "naming", "minimalism", "docstring", "security"]
    accepted: bool
    user_rating: int = Field(ge=1, le=5)


class FeedbackResponse(BaseModel):
    status: Literal["queued", "error"]
    message: str
    request_id: str


class AgentWeightsResponse(BaseModel):
    style: float
    naming: float
    minimalism: float
    docstring: float
    security: float
    request_id: str

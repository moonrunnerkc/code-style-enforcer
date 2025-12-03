# Author: Bradley R. Kinnard — all agents inherit from this or they don't exist

"""ABC for agents. LLM returns {"suggestions": [...]}, we pack it into AgentResult."""

from abc import ABC, abstractmethod
from typing import Literal

from src.backend.core.models import AgentResult, Suggestion


AgentName = Literal["style", "naming", "minimalism", "docstring", "security"]


class BaseAgent(ABC):

    name: AgentName

    def __init__(self, name: AgentName):
        self.name = name

    @abstractmethod
    async def analyze(self, code: str, language: str) -> AgentResult:
        """override this. if LLM craps out, return empty suggestions + error field"""
        ...

    def _make_result(
        self,
        suggestions: list[Suggestion],
        took_ms: int,
        error: str | None = None
    ) -> AgentResult:
        return AgentResult(
            agent=self.name,
            suggestions=suggestions,
            took_ms=took_ms,
            error=error
        )

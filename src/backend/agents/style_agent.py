# Author: Bradley R. Kinnard — tabs vs spaces, the eternal war

"""Style agent. Line length, formatting, whitespace, the cosmetic stuff."""

import json
import time
import uuid

from src.backend.agents.base_agent import BaseAgent
from src.backend.adapters.llm_client import chat_json
from src.backend.core.models import AgentResult, Suggestion

# severity 5 = CRITICAL, 4 = ERROR, 3 = WARNING, 2 = INFO, 1 = HINT
SYSTEM = """You are a code style analyzer. You MUST respond with valid JSON only.

SEVERITY SCALE: 1=hint, 2=info, 3=warning (style issues are usually 1-3)

Focus on:
- line length (flag >100 chars) → severity 2
- inconsistent indentation → severity 3
- trailing whitespace → severity 1
- blank line usage → severity 1
- bracket/brace placement → severity 2

Response format:
{"suggestions": [{"type": "style-issue-type", "message": "description", "severity": 1-3, "confidence": 0.0-1.0}]}

Be specific about line numbers. Skip nitpicks. If code looks fine, return {"suggestions": []}."""


class StyleAgent(BaseAgent):

    def __init__(self):
        super().__init__("style")

    async def analyze(self, code: str, language: str) -> AgentResult:
        start = time.perf_counter()
        try:
            resp = await chat_json(SYSTEM, f"Language: {language}\n\n```\n{code}\n```")
            data = json.loads(resp.content)
            suggestions = [
                Suggestion(
                    id=f"sty-{uuid.uuid4().hex[:8]}",
                    agent=self.name,
                    type=s.get("type", "style"),
                    message=s["message"],
                    severity=min(3, max(1, s.get("severity", 2))),  # style caps at 3
                    confidence=s.get("confidence", 0.7),
                    score=0.0
                )
                for s in data.get("suggestions", [])
            ]
            took = int((time.perf_counter() - start) * 1000)
            return self._make_result(suggestions, took)
        except Exception as e:
            took = int((time.perf_counter() - start) * 1000)
            return self._make_result([], took, error=str(e))

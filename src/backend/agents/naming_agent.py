# Author: Bradley R. Kinnard — x, y, z are not variable names

"""Naming agent. Variables, functions, classes, constants. Make them readable."""

import json
import time
import uuid

from src.backend.agents.base_agent import BaseAgent
from src.backend.adapters.llm_client import chat_json
from src.backend.core.models import AgentResult, Suggestion

# severity 5 = CRITICAL, 4 = ERROR, 3 = WARNING, 2 = INFO, 1 = HINT
SYSTEM = """You are a naming convention analyzer. You MUST respond with valid JSON only.

SEVERITY SCALE: 1=hint, 2=info, 3=warning, 4=error (naming issues cap at 4)

Look for:
- Actively misleading names (e.g., 'data' that holds a user) → severity 4
- Single letter variables except i,j,k in loops → severity 3
- Inconsistent casing (mixing camelCase and snake_case) → severity 3
- Abbreviations that aren't obvious → severity 2
- Boolean names that don't read as questions → severity 2

Response format:
{"suggestions": [{"type": "naming-issue-type", "message": "description", "severity": 1-4, "confidence": 0.0-1.0}]}

If naming looks fine, return {"suggestions": []}."""


class NamingAgent(BaseAgent):

    def __init__(self):
        super().__init__("naming")

    async def analyze(self, code: str, language: str) -> AgentResult:
        t0 = time.perf_counter()
        try:
            resp = await chat_json(SYSTEM, f"{language} code:\n```\n{code}\n```")
            raw = json.loads(resp.content)
            sug = []
            for s in raw.get("suggestions", []):
                sug.append(Suggestion(
                    id=f"nam-{uuid.uuid4().hex[:8]}",
                    agent=self.name,
                    type=s.get("type", "naming"),
                    message=s["message"],
                    severity=min(4, max(1, s.get("severity", 2))),  # naming caps at 4
                    confidence=s.get("confidence", 0.75),
                    score=0.0
                ))
            ms = int((time.perf_counter() - t0) * 1000)
            return self._make_result(sug, ms)
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return self._make_result([], ms, error=str(e))

# Author: Bradley R. Kinnard — document the why, not the what

"""Docstring agent. Missing docs, bad docs, misleading docs."""

import json
import time
import uuid

from src.backend.agents.base_agent import BaseAgent
from src.backend.adapters.llm_client import chat_json
from src.backend.core.models import AgentResult, Suggestion

# severity 5 = CRITICAL, 4 = ERROR, 3 = WARNING, 2 = INFO, 1 = HINT
SYSTEM = """You are a documentation analyzer. You MUST respond with valid JSON only.

SEVERITY SCALE: 1=hint, 2=info, 3=warning (doc issues cap at 3)

Review docstrings and comments. Flag:
- Public API with no docstring → severity 3
- Misleading or outdated docs → severity 3
- Missing parameter/return docs on complex functions → severity 2
- Docstrings that just repeat the function name → severity 2
- TODO/FIXME that should be tickets → severity 1

IMPORTANT: Do NOT flag code logic issues (like duplicate function calls).
Only flag documentation issues. Leave code quality to other agents.

Response format:
{"suggestions": [{"type": "doc-issue-type", "message": "description", "severity": 1-3, "confidence": 0.0-1.0}]}

If docs look fine, return {"suggestions": []}."""


class DocstringAgent(BaseAgent):

    def __init__(self):
        super().__init__("docstring")

    async def analyze(self, code: str, language: str) -> AgentResult:
        t = time.perf_counter()
        try:
            resp = await chat_json(SYSTEM, f"{language}:\n```\n{code}\n```")
            data = json.loads(resp.content)
            sug = [
                Suggestion(
                    id=f"doc-{uuid.uuid4().hex[:8]}",
                    agent=self.name,
                    type=s.get("type", "docstring"),
                    message=s["message"],
                    severity=min(3, max(1, s.get("severity", 2))),  # docs cap at 3
                    confidence=s.get("confidence", 0.7),
                    score=0.0
                )
                for s in data.get("suggestions", [])
            ]
            return self._make_result(sug, int((time.perf_counter() - t) * 1000))
        except Exception as e:
            return self._make_result([], int((time.perf_counter() - t) * 1000), str(e))

# Author: Bradley R. Kinnard — x, y, z are not variable names

"""
Naming agent. Complains about bad variable names, misleading function names,
inconsistent casing. Won't go higher than severity 4 because naming alone
doesn't break production (usually).
"""

import json
import time
import uuid

from src.backend.agents.base_agent import BaseAgent
from src.backend.adapters.llm_client import chat_json
from src.backend.core.models import AgentResult, Suggestion


# prompt lives here so I can tweak it without scrolling through class methods
NAMING_PROMPT = """Analyze variable/function/class names in this code. Return JSON.

Bad naming patterns to catch:
- Misleading names like 'data' when it's actually a User object (sev 4)
- Single letters outside of loop indices (sev 3)  
- Mixed casing styles in same file, snake_case vs camelCase (sev 3)
- Cryptic abbreviations like 'usr_mgr_svc' (sev 2)
- Booleans that don't read like yes/no questions (sev 2)

Keep severity at 4 max. Naming is annoying but rarely a prod incident.

JSON format: {"suggestions": [{"type": "...", "message": "...", "severity": 1-4, "confidence": 0.0-1.0}]}
Empty array if names look fine."""


class NamingAgent(BaseAgent):

    def __init__(self):
        super().__init__("naming")

    async def analyze(self, code: str, language: str) -> AgentResult:
        start = time.perf_counter()

        try:
            llm_resp = await chat_json(NAMING_PROMPT, f"{language}:\n```\n{code}\n```")
            parsed = json.loads(llm_resp.content)
        except Exception as err:
            elapsed = int((time.perf_counter() - start) * 1000)
            return self._make_result([], elapsed, error=str(err))

        suggestions = []
        for item in parsed.get("suggestions", []):
            # clamp severity: naming issues shouldn't exceed 4
            sev = item.get("severity", 2)
            if sev > 4:
                sev = 4
            if sev < 1:
                sev = 1

            suggestions.append(Suggestion(
                id=f"nam-{uuid.uuid4().hex[:8]}",
                agent=self.name,
                type=item.get("type", "naming"),
                message=item["message"],
                severity=sev,
                confidence=item.get("confidence", 0.75),
                score=0.0
            ))

        elapsed = int((time.perf_counter() - start) * 1000)
        return self._make_result(suggestions, elapsed)

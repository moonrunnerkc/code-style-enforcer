# Author: Bradley R. Kinnard — trust no input

"""Security agent. AST-based async leak detection + LLM for injection/secrets."""

import ast
import json
import time
import uuid

from src.backend.agents.base_agent import BaseAgent
from src.backend.adapters.llm_client import chat_json
from src.backend.core.models import AgentResult, Suggestion


def _find_unawaited_tasks(code: str) -> list[Suggestion]:
    """AST scan for asyncio.create_task() not stored/cancelled. severity=5."""
    suggestions: list[Suggestion] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        # look for create_task calls
        if isinstance(node, ast.Call):
            func = node.func
            is_create_task = False

            if isinstance(func, ast.Attribute) and func.attr == "create_task":
                is_create_task = True
            elif isinstance(func, ast.Name) and func.id == "create_task":
                is_create_task = True

            if is_create_task:
                # check if it's a bare expression (not stored)
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.Expr) and parent.value is node:
                        suggestions.append(Suggestion(
                            id=f"sec-{uuid.uuid4().hex[:8]}",
                            agent="security",
                            type="unawaited-task",
                            message=f"CRITICAL: asyncio.create_task() on line {node.lineno} not stored or awaited. Memory leak and potential DoS.",
                            severity=5,
                            confidence=1.0,
                            score=0.0
                        ))
                        break

    return suggestions


def _find_infinite_loops(code: str) -> list[Suggestion]:
    """AST scan for while True without break/return/cancel. severity=5."""
    suggestions: list[Suggestion] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            # check if condition is literally True
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                # look for break, return, or cancel in body
                has_exit = False
                for child in ast.walk(node):
                    if isinstance(child, (ast.Break, ast.Return)):
                        has_exit = True
                        break
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute) and child.func.attr == "cancel":
                            has_exit = True
                            break

                if not has_exit:
                    suggestions.append(Suggestion(
                        id=f"sec-{uuid.uuid4().hex[:8]}",
                        agent="security",
                        type="infinite-loop",
                        message=f"CRITICAL: while True loop on line {node.lineno} has no break/return. Memory leak and DoS vector.",
                        severity=5,
                        confidence=0.95,
                        score=0.0
                    ))

    return suggestions


# LLM for nuanced security issues AST can't catch
SYSTEM = """You are a security analyzer. Respond with valid JSON only.
Focus on: SQL injection, hardcoded secrets, unsafe deserialization, shell injection.
Do NOT flag async/loop issues - that's handled separately.

Response format: {"suggestions": [{"type": "...", "message": "...", "severity": 1-5, "confidence": 0.0-1.0}]}
severity 5=exploitable, 4=high risk, 3=input validation. If safe, return {"suggestions": []}"""


class SecurityAgent(BaseAgent):

    def __init__(self):
        super().__init__("security")

    async def analyze(self, code: str, language: str) -> AgentResult:
        t0 = time.perf_counter()
        results: list[Suggestion] = []

        # AST-based detection first (deterministic, fast, critical)
        if language.lower() == "python":
            results.extend(_find_unawaited_tasks(code))
            results.extend(_find_infinite_loops(code))

        # LLM for injection/secrets
        try:
            resp = await chat_json(SYSTEM, f"Review for security:\n```{language}\n{code}\n```")
            raw = json.loads(resp.content)
            for s in raw.get("suggestions", []):
                results.append(Suggestion(
                    id=f"sec-{uuid.uuid4().hex[:8]}",
                    agent=self.name,
                    type=s.get("type", "security"),
                    message=s["message"],
                    severity=min(5, max(1, s.get("severity", 4))),
                    confidence=s.get("confidence", 0.9),
                    score=0.0
                ))
        except Exception as ex:
            if not results:
                elapsed = int((time.perf_counter() - t0) * 1000)
                return self._make_result([], elapsed, error=str(ex))

        elapsed = int((time.perf_counter() - t0) * 1000)
        return self._make_result(results, elapsed)

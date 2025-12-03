# Author: Bradley R. Kinnard — less is more, unless it's tests

"""Minimalism agent. AST-based duplicate detection + LLM fallback for nuanced issues."""

import ast
import json
import time
import uuid
from collections import defaultdict

from src.backend.agents.base_agent import BaseAgent
from src.backend.adapters.llm_client import chat_json
from src.backend.core.models import AgentResult, Suggestion


def _get_call_signature(node: ast.Call, code_lines: list[str]) -> str:
    """Extract a canonical signature for a Call node: func name + args as source."""
    try:
        # get function name
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id
        else:
            func_name = ast.dump(node.func)

        # get args as source text for exact comparison
        args_src = []
        for arg in node.args:
            if hasattr(arg, 'lineno') and hasattr(arg, 'end_lineno'):
                # slice from source
                start_line = arg.lineno - 1
                end_line = arg.end_lineno
                if start_line < len(code_lines):
                    args_src.append(ast.unparse(arg))
            else:
                args_src.append(ast.dump(arg))

        for kw in node.keywords:
            args_src.append(f"{kw.arg}={ast.unparse(kw.value)}")

        return f"{func_name}({', '.join(args_src)})"
    except Exception:
        return ast.dump(node)


def _find_duplicate_calls(code: str) -> list[Suggestion]:
    """AST scan for duplicate await/call expressions within same function. severity=5."""
    suggestions: list[Suggestion] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # let LLM handle broken code

    code_lines = code.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # collect all await calls in this function
        await_calls: dict[str, list[int]] = defaultdict(list)

        for child in ast.walk(node):
            if isinstance(child, ast.Await) and isinstance(child.value, ast.Call):
                sig = _get_call_signature(child.value, code_lines)
                await_calls[sig].append(child.lineno)

        # flag duplicates
        for sig, lines in await_calls.items():
            if len(lines) >= 2:
                suggestions.append(Suggestion(
                    id=f"min-{uuid.uuid4().hex[:8]}",
                    agent="minimalism",
                    type="duplicate-await",
                    message=f"CRITICAL: `{sig}` called {len(lines)} times (lines {', '.join(map(str, lines))}). Doubles cost and latency.",
                    severity=5,
                    confidence=1.0,
                    score=0.0
                ))

    return suggestions


def _find_mutable_defaults(code: str) -> list[Suggestion]:
    """AST scan for module-level mutable defaults (dict/list/set). severity=5."""
    suggestions: list[Suggestion] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    # check if value is mutable
                    if isinstance(node.value, (ast.Dict, ast.List, ast.Set)):
                        suggestions.append(Suggestion(
                            id=f"min-{uuid.uuid4().hex[:8]}",
                            agent="minimalism",
                            type="mutable-default",
                            message=f"CRITICAL: `{target.id}` is a module-level mutable default (line {node.lineno}). Use frozenset/tuple or move to function.",
                            severity=5,
                            confidence=1.0,
                            score=0.0
                        ))

    return suggestions


# LLM prompt for nuanced issues AST can't catch
SYSTEM = """You are a code minimalism analyzer. Respond with valid JSON only.
Focus on issues AST analysis might miss: unused imports, dead code paths, redundant logic.
Do NOT flag duplicate function calls - that's handled separately.

Response format: {"suggestions": [{"type": "...", "message": "...", "severity": 1-5, "confidence": 0.0-1.0}]}
severity 3=unused imports, 2=simplification, 1=nits. If clean, return {"suggestions": []}"""


class MinimalismAgent(BaseAgent):

    def __init__(self):
        super().__init__("minimalism")

    async def analyze(self, code: str, language: str) -> AgentResult:
        start = time.perf_counter()
        results: list[Suggestion] = []

        # AST-based detection first (deterministic, fast, critical issues)
        if language.lower() == "python":
            results.extend(_find_duplicate_calls(code))
            results.extend(_find_mutable_defaults(code))

        # LLM for nuanced issues
        try:
            resp = await chat_json(SYSTEM, f"```{language}\n{code}\n```")
            parsed = json.loads(resp.content)
            for s in parsed.get("suggestions", []):
                results.append(Suggestion(
                    id=f"min-{uuid.uuid4().hex[:8]}",
                    agent=self.name,
                    type=s.get("type", "minimalism"),
                    message=s["message"],
                    severity=min(4, max(1, s.get("severity", 2))),  # LLM caps at 4, AST owns 5
                    confidence=s.get("confidence", 0.8),
                    score=0.0
                ))
        except Exception as ex:
            # AST results still valid even if LLM fails
            if not results:
                elapsed = int((time.perf_counter() - start) * 1000)
                return self._make_result([], elapsed, error=str(ex))

        elapsed = int((time.perf_counter() - start) * 1000)
        return self._make_result(results, elapsed)

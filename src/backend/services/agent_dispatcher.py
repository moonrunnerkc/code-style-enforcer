# Author: Bradley R. Kinnard — parallelism or bankruptcy

"""Run all agents in parallel with strict timeouts. One slow agent won't tank the whole request."""

import asyncio
import logging
import time

from src.backend.agents.base_agent import BaseAgent
from src.backend.agents.style_agent import StyleAgent
from src.backend.agents.naming_agent import NamingAgent
from src.backend.agents.minimalism_agent import MinimalismAgent
from src.backend.agents.docstring_agent import DocstringAgent
from src.backend.agents.security_agent import SecurityAgent
from src.backend.core.models import AgentResult

log = logging.getLogger(__name__)

AGENT_TIMEOUT = 8.0  # per agent, seconds
TOTAL_TIMEOUT = 12.0  # whole dispatch, hard cap

# lazy init so we don't spin up agents on import
_agents: list[BaseAgent] | None = None


def _get_agents() -> list[BaseAgent]:
    global _agents
    if _agents is None:
        _agents = [
            StyleAgent(),
            NamingAgent(),
            MinimalismAgent(),
            DocstringAgent(),
            SecurityAgent(),
        ]
    return _agents


async def _run_agent(agent: BaseAgent, code: str, language: str) -> AgentResult:
    """Run single agent with timeout. Never raises, returns error result instead."""
    try:
        return await asyncio.wait_for(
            agent.analyze(code, language),
            timeout=AGENT_TIMEOUT
        )
    except asyncio.TimeoutError:
        log.warning(f"{agent.name} timed out after {AGENT_TIMEOUT}s")
        return AgentResult(agent=agent.name, suggestions=[], took_ms=int(AGENT_TIMEOUT * 1000), error="timeout")
    except Exception as e:
        log.exception(f"{agent.name} crashed: {e}")
        return AgentResult(agent=agent.name, suggestions=[], took_ms=0, error=str(e))


async def dispatch(code: str, language: str) -> list[AgentResult]:
    """
    Fire all agents in parallel, collect results.
    Timeouts and crashes are logged but don't fail the whole thing.
    """
    agents = _get_agents()
    start = time.perf_counter()

    tasks = [_run_agent(a, code, language) for a in agents]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=TOTAL_TIMEOUT
        )
    except asyncio.TimeoutError:
        # shouldn't happen if AGENT_TIMEOUT < TOTAL_TIMEOUT, but just in case
        log.error(f"dispatch hit total timeout of {TOTAL_TIMEOUT}s")
        results = []

    # gather with return_exceptions=True can return Exception objects
    final: list[AgentResult] = []
    for i, r in enumerate(results):
        if isinstance(r, AgentResult):
            final.append(r)
        elif isinstance(r, Exception):
            agent_name = agents[i].name
            log.error(f"unexpected exception from {agent_name}: {r}")
            final.append(AgentResult(agent=agent_name, suggestions=[], took_ms=0, error=str(r)))

    elapsed = int((time.perf_counter() - start) * 1000)
    log.info(f"dispatch finished in {elapsed}ms with {len(final)} results")
    return final

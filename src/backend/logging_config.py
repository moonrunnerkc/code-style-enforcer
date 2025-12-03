# Author: Bradley R. Kinnard — logs or it didn't happen

"""Structlog config. JSON in prod, pretty in dev. Request ID injected from context."""

import logging
import os
import sys
from contextvars import ContextVar
import structlog

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(rid: str) -> None:
    request_id_ctx.set(rid)


def _add_request_id(logger, method, event_dict):
    rid = request_id_ctx.get()
    event_dict["request_id"] = rid or "No request_id found. Someone forgot middleware. This is fine."
    return event_dict


def setup_logging(level: str = "INFO") -> None:
    """Wire up structlog once from lifespan. VERBOSE env var for colorful dev output."""
    is_dev = os.getenv("VERBOSE", "").lower() in ("1", "true", "yes")

    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    renderer = structlog.dev.ConsoleRenderer(colors=True) if is_dev else structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

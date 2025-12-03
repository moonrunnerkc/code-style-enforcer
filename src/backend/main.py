# Author: Bradley R. Kinnard — because code doesn't critique itself.

"""
Five parallel agents critique your code, RL tweaks the weights based on what you actually listen to.
Health endpoint only for now. The rest comes later.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator
import logging
import uuid

from fastapi import FastAPI, Request
import uvicorn
from src.backend.api.routes_health import router as health_router
from src.backend.api.routes_code import router as code_router
from src.backend.api.routes_feedback import router as feedback_router
from src.backend.api.routes_agents import router as agents_router
from src.backend.logging_config import setup_logging, set_request_id

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # logging now, redis/dynamo/sqs later
    setup_logging(level="INFO")
    logger.info("Service started; waiting for requests")
    yield
    logger.info("Shutdown signal received; wrapping up")


app = FastAPI(
    title="Code Style Enforcer",
    version="0.1.0",
    lifespan=lifespan
)


@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    # ALB might send one, otherwise make it up
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = rid
    set_request_id(rid)  # push to structlog context
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


app.include_router(health_router, prefix="/api/v1")
app.include_router(code_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)

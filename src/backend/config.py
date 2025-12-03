# Author: Bradley R. Kinnard — env vars or bust

"""
Settings via pydantic-settings. Reads from env, falls back to .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    openai_api_key: str = ""  # required for LLM calls
    openai_model: str = "gpt-4o"
    llm_timeout: int = 30
    max_code_bytes: int = 100_000  # 100KB, reject bigger payloads
    aws_region: str = "us-east-1"

    # local dev endpoints
    dynamodb_endpoint: str | None = None  # http://localhost:8000 for local
    sqs_endpoint: str | None = None  # http://localhost:4566 for localstack

    # AWS creds for local dev
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_default_region: str | None = None

    # stub mode - generate fake suggestions without LLM
    stub_mode: bool = False  # set True to skip LLM calls

    # auth - comma separated list, or "dev" to skip auth
    valid_api_keys: str = "dev"
    rate_limit: int = 10  # requests per window
    rate_window: int = 60  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unknown env vars


settings = Settings()

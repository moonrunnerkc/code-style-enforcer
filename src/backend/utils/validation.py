# Author: Bradley R. Kinnard — garbage in, 413 out

"""Input validation. Reject bad requests before they waste LLM tokens."""

from fastapi import HTTPException, status

from src.backend.config import settings

SUPPORTED_LANGUAGES = {"python", "javascript", "typescript", "java", "go", "rust", "c", "cpp"}
VALID_DETAIL_LEVELS = {"fast", "normal", "deep"}


def validate_code_size(code: str) -> None:
    """Reject code over the size limit. No point analyzing a 10MB file."""
    size = len(code.encode("utf-8"))
    if size > settings.max_code_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"code too large: {size} bytes, max {settings.max_code_bytes}"
        )


def validate_language(language: str) -> None:
    """Check language is one we support. Case insensitive."""
    if language.lower() not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported language: {language}. try: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )


def validate_detail_level(level: str) -> None:
    """fast/normal/deep only."""
    if level not in VALID_DETAIL_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid detail_level: {level}. must be one of {VALID_DETAIL_LEVELS}"
        )


def validate_analyze_request(code: str, language: str, detail_level: str) -> None:
    """Run all validations. Call this from route before doing real work."""
    validate_code_size(code)
    validate_language(language)
    validate_detail_level(detail_level)

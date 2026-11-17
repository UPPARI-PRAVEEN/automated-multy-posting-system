import re
from datetime import date, time
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, field_validator


_URL_PATTERN = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_TRAILING_PUNCTUATION = ".,!?;:"
_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


def extract_cta_url(message: str) -> str:
    candidates: list[str] = []
    for match in _URL_PATTERN.finditer(message):
        candidate = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        while candidate.endswith(")") and candidate.count(")") > candidate.count("("):
            candidate = candidate[:-1]
        candidates.append(candidate)

    if len(candidates) != 1:
        raise ValueError("Message must contain exactly one CTA link.")

    url = candidates[0]
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("CTA link must be a valid HTTP or HTTPS URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("CTA link must not contain embedded credentials.")

    try:
        _HTTP_URL_ADAPTER.validate_python(url)
    except ValueError as exc:
        raise ValueError("CTA link must be a valid HTTP or HTTPS URL.") from exc
    return url


class PostingRequest(BaseModel):
    message: str = Field(min_length=1, max_length=200)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must not be blank.")
        extract_cta_url(value)
        return value


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None
    public_access: bool
    date: date | None
    time: time | None
    error: str | None


class PostingResponse(BaseModel):
    success: bool
    results: list[PlatformResult]

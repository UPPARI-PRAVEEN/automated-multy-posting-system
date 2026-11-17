from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


class PlatformError(Exception):
    """A safe-to-return error reported by a platform API."""


@dataclass
class PublishedPost:
    url: str | None
    public_access: bool
    published_at: datetime


class PlatformAdapter:
    name = "Platform"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def request_json(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            transport=self.transport,
            timeout=20.0,
        ) as client:
            response = await client.request(method, url, **kwargs)

        if not response.is_success:
            detail = response.text[:300].strip()
            message = f"Platform API returned HTTP {response.status_code}"
            if detail:
                message = f"{message}: {detail}"
            raise PlatformError(message)

        try:
            payload = response.json()
        except ValueError as exc:
            raise PlatformError("Platform API returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise PlatformError("Platform API returned an unexpected response.")
        return payload

    @staticmethod
    def parse_datetime(value: Any) -> datetime:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    @staticmethod
    def missing_configuration(*names: str) -> PlatformError:
        return PlatformError(
            "Missing required configuration: " + ", ".join(names)
        )

import logging
from datetime import datetime, timezone
from typing import Protocol

import httpx

from app.config import Settings
from app.platforms import (
    BlueskyPlatform,
    DevToPlatform,
    MastodonPlatform,
    TelegramPlatform,
)
from app.platforms.base import PlatformError, PublishedPost
from app.schemas import PlatformResult, PostingResponse

logger = logging.getLogger(__name__)


class Publisher(Protocol):
    name: str

    async def publish(self, message: str) -> PublishedPost: ...


class PostingService:
    def __init__(self, publishers: list[Publisher]) -> None:
        self.publishers = publishers

    async def post(self, message: str) -> PostingResponse:
        results: list[PlatformResult] = []
        for publisher in self.publishers:
            try:
                published = await publisher.publish(message)
                timestamp = published.published_at.astimezone(timezone.utc)
                results.append(
                    PlatformResult(
                        platform=publisher.name,
                        status="success",
                        posted_url=published.url,
                        public_access=published.public_access,
                        date=timestamp.date(),
                        time=timestamp.time().replace(tzinfo=None),
                        error=None,
                    )
                )
            except PlatformError as exc:
                results.append(self.failed_result(publisher.name, str(exc)))
            except httpx.RequestError as exc:
                logger.warning(
                    "%s request failed: %s",
                    publisher.name,
                    type(exc).__name__,
                )
                results.append(
                    self.failed_result(
                        publisher.name,
                        f"Network request failed ({type(exc).__name__}).",
                    )
                )
            except Exception as exc:
                logger.exception("%s integration failed unexpectedly", publisher.name)
                results.append(
                    self.failed_result(
                        publisher.name,
                        f"Unexpected integration error ({type(exc).__name__}).",
                    )
                )

        return PostingResponse(
            success=any(result.status == "success" for result in results),
            results=results,
        )

    @staticmethod
    def failed_result(platform: str, error: str) -> PlatformResult:
        return PlatformResult(
            platform=platform,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error=error,
        )


def create_posting_service(settings: Settings) -> PostingService:
    return PostingService(
        [
            MastodonPlatform(settings),
            BlueskyPlatform(settings),
            TelegramPlatform(settings),
            DevToPlatform(settings),
        ]
    )

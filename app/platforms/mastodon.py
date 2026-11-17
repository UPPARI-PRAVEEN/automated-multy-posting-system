from typing import Any

from app.config import Settings
from app.platforms.base import PlatformAdapter, PlatformError, PublishedPost


class MastodonPlatform(PlatformAdapter):
    name = "Mastodon"

    def __init__(self, settings: Settings, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings

    async def publish(self, message: str) -> PublishedPost:
        settings = self.settings
        if not settings.mastodon_instance_url or not settings.mastodon_access_token:
            raise self.missing_configuration(
                "MASTODON_INSTANCE_URL",
                "MASTODON_ACCESS_TOKEN",
            )
        if settings.mastodon_visibility not in {"public", "unlisted", "private", "direct"}:
            raise PlatformError(
                "MASTODON_VISIBILITY must be public, unlisted, private, or direct."
            )

        response = await self.request_json(
            "POST",
            f"{settings.mastodon_instance_url.rstrip('/')}/api/v1/statuses",
            headers={"Authorization": f"Bearer {settings.mastodon_access_token}"},
            json={"status": message, "visibility": settings.mastodon_visibility},
        )
        visibility = response.get("visibility", settings.mastodon_visibility)
        return PublishedPost(
            url=response.get("url"),
            public_access=visibility in {"public", "unlisted"},
            published_at=self.parse_datetime(response.get("created_at")),
        )

from app.config import Settings
from app.platforms.base import PlatformAdapter, PlatformError, PublishedPost


class DevToPlatform(PlatformAdapter):
    name = "DEV"

    def __init__(self, settings: Settings, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.settings = settings

    async def publish(self, message: str) -> PublishedPost:
        settings = self.settings
        if not settings.devto_api_key:
            raise self.missing_configuration("DEVTO_API_KEY")

        response = await self.request_json(
            "POST",
            "https://dev.to/api/articles",
            headers={"api-key": settings.devto_api_key},
            json={
                "article": {
                    "title": settings.devto_article_title,
                    "body_markdown": message,
                    "published": True,
                }
            },
        )
        post_url = response.get("url")
        if not post_url:
            raise PlatformError("DEV did not return a URL for the article.")
        return PublishedPost(
            url=post_url,
            public_access=response.get("published") is True,
            published_at=self.parse_datetime(response.get("published_at")),
        )

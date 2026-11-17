import base64
from typing import Any
from urllib.parse import quote

from app.config import Settings
from app.platforms.base import PlatformAdapter, PlatformError, PublishedPost


class RedditPlatform(PlatformAdapter):
    name = "Reddit"

    def __init__(self, settings: Settings, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings

    async def publish(self, message: str) -> PublishedPost:
        settings = self.settings
        missing: list[str] = []
        if not settings.reddit_client_id:
            missing.append("REDDIT_CLIENT_ID")
        if not settings.reddit_client_secret:
            missing.append("REDDIT_CLIENT_SECRET")
        if not settings.reddit_refresh_token:
            missing.append("REDDIT_REFRESH_TOKEN")
        if not settings.reddit_subreddit:
            missing.append("REDDIT_SUBREDDIT")
        if missing:
            raise self.missing_configuration(*missing)

        basic_token = base64.b64encode(
            f"{settings.reddit_client_id}:{settings.reddit_client_secret}".encode()
        ).decode()
        token = await self.request_json(
            "POST",
            "https://www.reddit.com/api/v1/access_token",
            headers={
                "Authorization": f"Basic {basic_token}",
                "User-Agent": "automated-multiplatform-posting/1.0",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": settings.reddit_refresh_token,
            },
        )
        access_token = token.get("access_token")
        if not isinstance(access_token, str):
            raise PlatformError("Reddit did not return an access token.")

        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "automated-multiplatform-posting/1.0",
        }
        subreddit = await self.request_json(
            "GET",
            f"https://oauth.reddit.com/r/{quote(settings.reddit_subreddit, safe='')}/about",
            headers=auth_headers,
        )
        subreddit_type = subreddit.get("data", {}).get("subreddit_type")

        response = await self.request_json(
            "POST",
            "https://oauth.reddit.com/api/submit",
            headers=auth_headers,
            data={
                "api_type": "json",
                "kind": "self",
                "sr": settings.reddit_subreddit,
                "title": settings.reddit_post_title,
                "text": message,
                "resubmit": "true",
            },
        )
        errors = response.get("json", {}).get("errors", [])
        if errors:
            raise PlatformError(f"Reddit rejected the post: {errors}")

        data: dict[str, Any] = response.get("json", {}).get("data", {})
        post_url = data.get("url")
        if not post_url:
            raise PlatformError("Reddit did not return a permalink for the post.")
        return PublishedPost(
            url=post_url,
            public_access=subreddit_type in {"public", "restricted"},
            published_at=self.parse_datetime(data.get("created_utc")),
        )

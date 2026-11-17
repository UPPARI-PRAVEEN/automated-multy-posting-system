from typing import Any

from app.config import Settings
from app.platforms.base import PlatformAdapter, PublishedPost
from app.schemas import extract_cta_url


class BlueskyPlatform(PlatformAdapter):
    name = "Bluesky"

    def __init__(self, settings: Settings, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings

    async def publish(self, message: str) -> PublishedPost:
        settings = self.settings
        if not settings.bluesky_identifier or not settings.bluesky_app_password:
            raise self.missing_configuration(
                "BLUESKY_IDENTIFIER",
                "BLUESKY_APP_PASSWORD",
            )

        pds_url = settings.bluesky_pds_url.rstrip("/")
        session = await self.request_json(
            "POST",
            f"{pds_url}/xrpc/com.atproto.server.createSession",
            json={
                "identifier": settings.bluesky_identifier,
                "password": settings.bluesky_app_password,
            },
        )
        access_jwt = session.get("accessJwt")
        did = session.get("did")
        if not isinstance(access_jwt, str) or not isinstance(did, str):
            raise ValueError("Bluesky session response did not include account credentials.")

        url = extract_cta_url(message)
        byte_start = len(message[: message.index(url)].encode("utf-8"))
        byte_end = byte_start + len(url.encode("utf-8"))
        record: dict[str, Any] = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": self.parse_datetime(None).isoformat().replace("+00:00", "Z"),
            "facets": [
                {
                    "index": {"byteStart": byte_start, "byteEnd": byte_end},
                    "features": [
                        {"$type": "app.bsky.richtext.facet#link", "uri": url}
                    ],
                }
            ],
        }
        created = await self.request_json(
            "POST",
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
        )
        uri = created.get("uri", "")
        rkey = uri.rsplit("/", 1)[-1]
        handle = session.get("handle") or settings.bluesky_identifier
        return PublishedPost(
            url=f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else None,
            public_access=True,
            published_at=self.parse_datetime(record["createdAt"]),
        )

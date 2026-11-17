import asyncio
import json
from urllib.parse import parse_qs

import httpx

from app.config import Settings
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.reddit import RedditPlatform
from app.platforms.telegram import TelegramPlatform


def test_mastodon_posts_with_requested_visibility() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/statuses"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert json.loads(request.content)["visibility"] == "public"
        return httpx.Response(
            200,
            json={
                "url": "https://mastodon.example/@alice/1",
                "visibility": "public",
                "created_at": "2026-11-16T12:30:00Z",
            },
        )

    platform = MastodonPlatform(
        Settings(
            mastodon_instance_url="https://mastodon.example",
            mastodon_access_token="test-token",
        ),
        transport=httpx.MockTransport(handler),
    )
    post = asyncio.run(platform.publish("Update https://example.com"))
    assert post.url == "https://mastodon.example/@alice/1"
    assert post.public_access is True
    assert post.published_at.isoformat() == "2026-11-16T12:30:00+00:00"


def test_bluesky_creates_a_post_with_link_facet() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("createSession"):
            return httpx.Response(
                200,
                json={
                    "accessJwt": "session-token",
                    "did": "did:plc:account",
                    "handle": "alice.example",
                },
            )
        record = json.loads(request.content)["record"]
        assert record["text"] == "Launch 🚀 https://example.com"
        assert record["facets"][0]["index"] == {
            "byteStart": len("Launch 🚀 ".encode()),
            "byteEnd": len("Launch 🚀 https://example.com".encode()),
        }
        assert record["facets"][0]["features"][0]["uri"] == "https://example.com"
        return httpx.Response(
            200,
            json={"uri": "at://did:plc:account/app.bsky.feed.post/record-key"},
        )

    platform = BlueskyPlatform(
        Settings(
            bluesky_identifier="alice.example",
            bluesky_app_password="app-password",
        ),
        transport=httpx.MockTransport(handler),
    )
    post = asyncio.run(platform.publish("Launch 🚀 https://example.com"))
    assert post.url == "https://bsky.app/profile/alice.example/post/record-key"
    assert post.public_access is True


def test_reddit_refreshes_token_and_submits_self_post() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/access_token"):
            assert request.headers["Authorization"].startswith("Basic ")
            assert b"grant_type=refresh_token" in request.content
            return httpx.Response(200, json={"access_token": "reddit-access"})
        assert request.headers["Authorization"] == "Bearer reddit-access"
        if request.method == "GET":
            assert request.url.path == "/r/mycommunity/about"
            return httpx.Response(
                200,
                json={"data": {"subreddit_type": "public"}},
            )
        fields = parse_qs(request.content.decode())
        assert fields["kind"] == ["self"]
        assert fields["sr"] == ["mycommunity"]
        assert fields["text"] == ["Update https://example.com"]
        return httpx.Response(
            200,
            json={"json": {"data": {"url": "https://reddit.com/r/mycommunity/1"}}},
        )

    platform = RedditPlatform(
        Settings(
            reddit_client_id="client",
            reddit_client_secret="secret",
            reddit_refresh_token="refresh",
            reddit_subreddit="mycommunity",
        ),
        transport=httpx.MockTransport(handler),
    )
    post = asyncio.run(platform.publish("Update https://example.com"))
    assert post.url == "https://reddit.com/r/mycommunity/1"
    assert post.public_access is True


def test_telegram_returns_public_permalink_when_configured() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/bottest-token/sendMessage"
        assert json.loads(request.content)["chat_id"] == "@mychannel"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 42,
                    "date": 1794832200,
                    "chat": {"username": "mychannel"},
                },
            },
        )

    platform = TelegramPlatform(
        Settings(
            telegram_bot_token="test-token",
            telegram_chat_id="@mychannel",
            telegram_public_channel="@mychannel",
        ),
        transport=httpx.MockTransport(handler),
    )
    post = asyncio.run(platform.publish("Update https://example.com"))
    assert post.url == "https://t.me/mychannel/42"
    assert post.public_access is True


def test_dev_publishes_article_and_returns_api_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["api-key"] == "dev-key"
        article = json.loads(request.content)["article"]
        assert article["published"] is True
        assert article["body_markdown"] == "Update https://example.com"
        return httpx.Response(
            200,
            json={
                "url": "https://dev.to/alice/update",
                "published_at": "2026-11-16T12:30:00Z",
                "published": True,
            },
        )

    platform = DevToPlatform(
        Settings(devto_api_key="dev-key"),
        transport=httpx.MockTransport(handler),
    )
    post = asyncio.run(platform.publish("Update https://example.com"))
    assert post.url == "https://dev.to/alice/update"
    assert post.public_access is True

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_posting_service
from app.platforms.base import PlatformError, PublishedPost
from app.services.posting_service import PostingService, create_posting_service


class FakePublisher:
    def __init__(self, name: str, should_fail: bool = False) -> None:
        self.name = name
        self.should_fail = should_fail

    async def publish(self, message: str) -> PublishedPost:
        if self.should_fail:
            raise PlatformError("API rejected the post.")
        return PublishedPost(
            url=f"https://social.example/{self.name}/123",
            public_access=True,
            published_at=datetime(2026, 11, 16, 12, 30, tzinfo=timezone.utc),
        )


def test_posting_continues_after_platform_failure() -> None:
    app.dependency_overrides[get_posting_service] = lambda: PostingService(
        [FakePublisher("first", should_fail=True), FakePublisher("second")]
    )
    try:
        response = TestClient(app).post(
            "/posting",
            json={"message": "Launch update https://example.com"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert [item["status"] for item in payload["results"]] == ["failed", "success"]
    assert payload["results"][0]["error"] == "API rejected the post."
    assert payload["results"][1]["posted_url"] == "https://social.example/second/123"
    assert payload["results"][1]["date"] == "2026-11-16"
    assert payload["results"][1]["time"] == "12:30:00"


def test_rejects_message_over_200_characters() -> None:
    response = TestClient(app).post(
        "/posting",
        json={"message": "x" * 201 + " https://example.com"},
    )
    assert response.status_code == 422


def test_rejects_missing_or_multiple_links() -> None:
    client = TestClient(app)
    missing = client.post("/posting", json={"message": "A message without a link"})
    multiple = client.post(
        "/posting",
        json={"message": "https://one.example https://two.example"},
    )
    assert missing.status_code == 422
    assert multiple.status_code == 422


def test_rejects_invalid_or_credential_bearing_link() -> None:
    client = TestClient(app)
    invalid = client.post("/posting", json={"message": "Visit https://"})
    credentials = client.post(
        "/posting",
        json={"message": "Visit https://user:pass@example.com"},
    )
    assert invalid.status_code == 422
    assert credentials.status_code == 422


def test_default_service_reports_each_unconfigured_platform() -> None:
    settings = Settings(
        mastodon_instance_url="",
        mastodon_access_token="",
        bluesky_identifier="",
        bluesky_app_password="",
        telegram_bot_token="",
        telegram_chat_id="",
        devto_api_key="",
    )
    app.dependency_overrides[get_posting_service] = lambda: create_posting_service(
        settings
    )
    try:
        response = TestClient(app).post(
            "/posting",
            json={"message": "Launch update https://example.com"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert [item["platform"] for item in payload["results"]] == [
        "Mastodon",
        "Bluesky",
        "Telegram",
        "DEV",
    ]
    assert all(item["status"] == "failed" for item in payload["results"])

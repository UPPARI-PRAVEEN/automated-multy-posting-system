from app.config import Settings
from app.platforms.base import PlatformAdapter, PlatformError, PublishedPost


class TelegramPlatform(PlatformAdapter):
    name = "Telegram"

    def __init__(self, settings: Settings, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.settings = settings

    async def publish(self, message: str) -> PublishedPost:
        settings = self.settings
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            raise self.missing_configuration("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")

        response = await self.request_json(
            "POST",
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": message},
        )
        if response.get("ok") is not True:
            description = response.get("description", "Telegram rejected the message.")
            raise PlatformError(str(description))

        result = response.get("result", {})
        message_id = result.get("message_id")
        chat = result.get("chat", {})
        channel = chat.get("username") or settings.telegram_public_channel.lstrip("@")
        post_url = f"https://t.me/{channel}/{message_id}" if channel and message_id else None
        return PublishedPost(
            url=post_url,
            public_access=post_url is not None,
            published_at=self.parse_datetime(result.get("date")),
        )

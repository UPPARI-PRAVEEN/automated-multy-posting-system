from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mastodon_instance_url: str = ""
    mastodon_access_token: str = ""
    mastodon_visibility: str = "public"

    bluesky_identifier: str = ""
    bluesky_app_password: str = ""
    bluesky_pds_url: str = "https://bsky.social"

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_refresh_token: str = ""
    reddit_subreddit: str = ""
    reddit_post_title: str = "New update"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_public_channel: str = ""

    devto_api_key: str = ""
    devto_article_title: str = "New update"


def get_settings() -> Settings:
    return Settings()

# Automated Multi-Platform Posting System

A FastAPI service that accepts one short message and attempts to publish it through the official APIs for Mastodon, Bluesky, Reddit, Telegram, and DEV. Each platform is handled independently: a platform error is included in that platform's result and does not stop the remaining integrations.

## Requirements and setup

- Python 3.10+
- API credentials and posting permissions for whichever platforms you want to use

From the project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add credentials. Leave an integration's credentials blank to receive a clear per-platform configuration error for that destination. Avoid committing `.env`.

Run the API:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Interactive API documentation: <http://localhost:4000/docs>

## API

`POST /posting` accepts a message of at most 200 characters with exactly one valid HTTP(S) URL:

```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

Validation errors return HTTP 422. Publishing attempts to all five configured integrations are sequential and independent. The top-level `success` value is true when at least one platform succeeds. A successful response contains the API-returned post URL when available, public-access state, and UTC date/time; a failed result contains the error and null date/time/URL fields. Telegram only returns a public URL when `TELEGRAM_PUBLIC_CHANNEL` is configured; a private chat post can succeed without being publicly accessible.

Example response shape (illustrative; actual values come from the platform API):

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@account/123",
      "public_access": true,
      "date": "2026-11-16",
      "time": "10:30:00",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing required configuration: BLUESKY_IDENTIFIER, BLUESKY_APP_PASSWORD"
    }
  ]
}
```

## Platform configuration

- **Mastodon:** set an instance URL, access token with `write:statuses`, and visibility. `public` and `unlisted` statuses are marked accessible.
- **Bluesky:** use your handle/identifier and an app password. The adapter creates a session and writes a post record with a rich-text facet for the CTA URL.
- **Reddit:** provide OAuth app credentials, a refresh token with read/submit permissions, and a target subreddit. A self-post uses the configured title and the submitted text. Public access is reported from the subreddit API's visibility setting.
- **Telegram:** provide the bot token and chat ID. Add the bot with permission to post in the target channel. Public channel permalinks use the username returned by Telegram, or `TELEGRAM_PUBLIC_CHANNEL` as a fallback.
- **DEV:** provide an API key; the message is published as the article body with the configured title.

## Run tests

```powershell
pytest
```

Tests use fake platform publishers and do not send real posts. To demonstrate live posting, configure authorized API credentials, start the server, submit the sample request from `/docs`, and retain the actual response (remove private data before sharing).

## Official API references

- [Mastodon: Create a status](https://docs.joinmastodon.org/methods/statuses/#create)
- [Bluesky: Create a record](https://docs.bsky.app/docs/api/com-atproto-repo-create-record) and [create a session](https://docs.bsky.app/docs/api/com-atproto-server-create-session)
- [Reddit API: Submit a post](https://www.reddit.com/dev/api/#POST_api_submit) and [OAuth2](https://github.com/reddit-archive/reddit/wiki/OAuth2)
- [Telegram Bot API: sendMessage](https://core.telegram.org/bots/api#sendmessage)
- [DEV API: Create an article](https://developers.forem.com/api/v1#tag/articles/operation/createArticle)

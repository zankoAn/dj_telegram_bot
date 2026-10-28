# Configuration

## Settings

| Setting | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Bot token from BotFather. |
| `TM_WEBHOOK_URL` | Yes | Base URL of the Bot API: `https://api.telegram.org` or your local Bot API server. |
| `PROXY_SOCKS` | No | SOCKS5 proxy as `IP:PORT`, used for every request to the Bot API. |

!!! note
    The client is created lazily on the first update. A missing `BOT_TOKEN` or `TM_WEBHOOK_URL` raises `ValueError` at that point.

## Proxy

You can configure a SOCKS5 proxy for your bot requests, including optional authentication credentials.

```python title="settings.py"
# Format: username:password@host:port
PROXY_SOCKS = "127.0.0.1:1080"
```

Requests go through `socks5h://PROXY_SOCKS`.

## Cache

The Django cache is used for:

- the sponsor membership check (60 seconds per user and channel)
- the maintenance-mode status (60 seconds)

!!! tip
    If you run several processes, use a shared cache backend (Redis, Memcached), otherwise each process keeps its own copy.

## Logging

All logs use the `dj_telegram_bot` logger namespace. The webhook view logs every incoming update at `INFO` and every unhandled exception at `ERROR`.

!!! info
    The webhook view always answers Telegram with `{"ok": true}`, so a failing handler does not make Telegram retry the update.

```python title="settings.py"
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"dj_telegram_bot": {"handlers": ["console"], "level": "INFO"}},
}
```

## Defaults of the send methods

- `parse_mode` defaults to `"html"` on **almost all** methods that accept it.
- Link previews are **disabled** by default in `send_message`. Pass `link_preview_options=LinkPreviewOptions(is_disabled=False)` to enable them.
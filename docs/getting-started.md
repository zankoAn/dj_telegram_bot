# Getting started

This page takes you from nothing to a bot that answers `/start`. It needs five short steps. Everything else is optional and can wait until you need it.

## 1. Install

=== "pip"

    ```bash
    pip install dj_telegram_bot
    ```

=== "uv"

    ```bash
    uv add dj_telegram_bot
    ```

## 2. Settings

```python title="settings.py"
INSTALLED_APPS = [
    ...
    "dj_telegram_bot.contrib",
]

BOT_TOKEN = "your-telegram-bot-token"
TM_WEBHOOK_URL = "https://api.telegram.org"  # or your local Bot API server(TDLib)
```

See [Configuration](configuration.md) for every setting.

## 3. URLs and migrations

```python title="urls.py"
from django.urls import path, include

urlpatterns = [
    ...
    path("telegram/", include("dj_telegram_bot.contrib.urls")),
]
```
=== "python"

    ```bash
    python manage.py migrate
    ```

=== "uv"

    ```bash
    uv run manage.py migrate
    ```

## 4. Set the webhook

Run this once in your terminal. Replace `<BOT_TOKEN>` with your bot's token (from BotFather) and `yourdomain.com` with the domain your Django site runs on:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://yourdomain.com/telegram/webhook/"
```

Telegram answers `"Webhook was set"`.

!!! note "No public domain? Use a local Bot API server"
    - **Official API:** the webhook `url` must be a public HTTPS domain.
    - **Local Bot API server (TDLib):** replace `https://api.telegram.org` with your TDLib server address (for example `http://127.0.0.1:8081`). The webhook `url` can then be your Django `ip:port`.

## 5. Write your first handler

Create a `bot_handlers/` package in any Django app. Every `.py` file in it (except files starting with `_`) is imported at startup, so the handlers inside are registered automatically:

```text
your_app/
└── bot_handlers/
    └── start.py
```

```python title="your_app/bot_handlers/start.py"
from dj_telegram_bot.core.handlers import command_handler

@command_handler("start")
def start(ctx):
    ctx.bot.send_message(ctx.chat_id, "Hello!")
```

Start Django, open your bot in Telegram and send `/start`. It answers **Hello!**

## What next?

Pick the line that matches what you want to do:

| I want to... | Read |
| --- | --- |
| reply to other commands, messages and buttons | [Handlers](handlers.md) |
| copy a working example | [Examples](examples.md) |
| build a conversation ("what's your name?" → answer) | [Steps](handlers.md#steps), which need a [user model](users.md) |
| limit a command to staff, or require joining a channel | [Access control](access-control.md) |
| block users or pause the bot | [Before handlers](before-handlers.md) |
| edit texts and keyboards without redeploying | [Messages & keyboards](admin.md) |

## If something doesn't work

??? question "Telegram never reaches your server"

    Ask Telegram what it sees (use your local server's address instead if you run one):

    ```bash
    curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
    ```

    `last_error_message` says why delivery failed, and `pending_update_count` shows updates that are waiting.

??? question "The bot never answers"

    Check your logs. If a module in `bot_handlers/` raises on import, the error is logged and the module is skipped.

??? question "`/start` works but `/start something` doesn't"

    The trigger must match the whole text after the slash. Use `"start*"`. See [command arguments](handlers.md#triggers-and-wildcards).

??? question "Nothing happens and there is no error"

    An update that matches no handler is silently ignored.

## Handlers outside `bot_handlers/`

??? note "Handlers in `views.py` or another module"

    If your handlers live elsewhere (for example in `views.py`), import that module yourself so the decorators run. `apps.py` is a good place:

    ```python title="your_app/apps.py"
    from django.apps import AppConfig

    class YourAppConfig(AppConfig):
        name = "your_app"

        def ready(self):
            from . import views  # wherever your handlers live
    ```
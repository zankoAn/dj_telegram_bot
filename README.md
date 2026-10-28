<div align="center">

<img src="https://raw.githubusercontent.com/zankoAn/dj_telegram_bot/main/assets/logo.svg" alt="dj_telegram_bot logo" width="96" height="96">

# Django Telegram Bot

**Build Telegram bots like your Django apps.**

Decorator routing · Messages and keyboards in the admin · Fully typed

[![PyPI](https://img.shields.io/pypi/v/dj-telegram-bot?color=2AABEE&label=PyPI)](https://pypi.org/project/dj-telegram-bot/)
[![License: MIT](https://img.shields.io/badge/license-MIT-6C5CE7.svg)](#license)
[![Docs](https://img.shields.io/badge/docs-mkdocs-2AABEE)](https://zankoan.github.io/dj_telegram_bot/)
[![Django Packages](https://img.shields.io/badge/Django_Packages-dj--telegram--bot-8c3c26.svg)](https://djangopackages.org/packages/p/dj-telegram-bot/)

[**Documentation**](https://zankoan.github.io/dj_telegram_bot/) ·
[**Getting started**](https://zankoan.github.io/dj_telegram_bot/getting-started/) ·
[**Examples**](https://zankoan.github.io/dj_telegram_bot/examples/) ·
[**Migration guide**](https://zankoan.github.io/dj_telegram_bot/migration/)

</div>

<br>

https://github.com/user-attachments/assets/5307e4c1-4f2a-4c2f-94e7-b05d9fec2788

<br>

## Why dj_telegram_bot?

The fastest way to build a production-ready Telegram bot on Django. You write plain functions, decorate them with a trigger, and the library does the routing. Your texts and keyboards live in the database, so you can change them from the admin without a redeploy.

```python
from dj_telegram_bot.core.guards import staff_required
from dj_telegram_bot.core.handlers import callback_handler, command_handler

@command_handler("start")
def start(ctx):
    ctx.bot.send_message(ctx.chat_id, "Hello!")

@callback_handler("buy_*")
def buy(ctx):
    item = ctx.callback_data.removeprefix("buy_")
    ctx.bot.answer_callback_query(ctx.callback_query.id, text=f"Added {item}")

@command_handler("stats")
@staff_required
def stats(ctx):
    ctx.bot.send_message(ctx.chat_id, "Staff only!")
```

## Features

| | |
| --- | --- |
| 🧭 **Decorator routing** | `@command_handler`, `@message_handler`, `@callback_handler`, `@inline_handler`, `@chosen_handler`, plus step handlers and `*` wildcards |
| 🧩 **Function or class handlers** | Use whichever style you like. Classes inherit from `UpdateHandler`, and everything is imported from `dj_telegram_bot.core.handlers` |
| ⌨️ **Edit from the admin** | Build messages and keyboards visually in the Django admin. No redeploy |
| 🛡️ **Built-in guards** | `@sponsor_required`, `@staff_required`, `@superuser_required`, and `@before_handler` for your own checks |
| 👤 **Optional user model** | Let the bot create users, bring your own model, or use none at all |
| 🔒 **Fully typed** | The whole Telegram Bot API is modeled with Pydantic, with autocomplete everywhere |
| 🛠️ **Maintenance mode** | Pause the bot and show a custom message, from the admin or from code |
| 🌐 **Proxy and local server** | SOCKS5 proxy and local Bot API server (TDLib) support |

## Install

```bash
pip install dj_telegram_bot
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv add dj_telegram_bot
```

> **Upgrading from 0.1.x?** Read the [Migration guide](https://zankoan.github.io/dj_telegram_bot/migration/).

## Quick start

**1. Settings**

```python
# settings.py
INSTALLED_APPS = [..., "dj_telegram_bot.contrib"]

BOT_TOKEN = "your-telegram-bot-token"
TM_WEBHOOK_URL = "https://api.telegram.org"  # or your local Bot API server
```

**2. URLs and migrations**

```python
# urls.py
urlpatterns = [..., path("telegram/", include("dj_telegram_bot.contrib.urls"))]
```

```bash
python manage.py migrate
```

**3. Set the webhook** (once)

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://yourdomain.com/telegram/webhook/"
```

**4. Write your first handler**

```python
# your_app/bot_handlers/start.py  (auto-discovered)
from dj_telegram_bot.core.handlers import command_handler

@command_handler("start")
def start(ctx):
    ctx.bot.send_message(ctx.chat_id, "Hello!")
```

Open your bot in Telegram and send `/start`. It answers **Hello!** 🎉

## How it works

```text
Telegram ──webhook──▶ Dispatcher ──▶ before handlers ──▶ Router ──▶ your function
```

Every update is wrapped in a handler object, passes through your `@before_handler` checks, and the router picks the first match: exact trigger, then the user's step, then wildcards.

## Documentation

| I want to... | Read |
| --- | --- |
| reply to commands, messages and buttons | [Handlers](https://zankoan.github.io/dj_telegram_bot/handlers/) |
| copy a working example | [Examples](https://zankoan.github.io/dj_telegram_bot/examples/) |
| build a conversation | [Steps](https://zankoan.github.io/dj_telegram_bot/handlers/#steps) and [User model](https://zankoan.github.io/dj_telegram_bot/users/) |
| limit a command or require joining a channel | [Access control](https://zankoan.github.io/dj_telegram_bot/access-control/) |
| block users or pause the bot | [Before handlers](https://zankoan.github.io/dj_telegram_bot/before-handlers/) |
| edit texts and keyboards without redeploying | [Messages & keyboards](https://zankoan.github.io/dj_telegram_bot/admin/) |
| upgrade from 0.1.x | [Migration guide](https://zankoan.github.io/dj_telegram_bot/migration/) |

Full guide: **https://zankoan.github.io/dj_telegram_bot/**

## Contributing

Contributions are welcome! Found a bug, have an idea, or spotted a typo in the docs? Open an issue or send a pull request.

Please keep pull requests **small and focused**

## License

[MIT](LICENSE)
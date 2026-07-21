# Django Telegram Bot

The fastest way to build a production-ready Telegram bot on Django.

---

## 🚀 Overview

`dj_telegram_bot` gives you a clean, decorator-based way to handle Telegram updates (commands, messages, callbacks) inside any Django project.

- Fully typed with Pydantic — every Telegram API type is modeled, giving you autocomplete and type safety everywhere
- Dynamic messages and keyboards — create and edit them directly from a custom Django admin UI
- Built-in `@sponsor_required` decorator — force users to join one or more channels (configured in the django-admin)
- Update mode — pause the bot and show a custom message (configured in the django-admin)
- Proxy (SOCKS5) support — for connecting to Telegram's official API (`api.telegram.org`) through a proxy, if needed.

---

## ⚙️ Installation

```bash
pip install dj_telegram_bot
```

or with `uv`:

```bash
uv add dj_telegram_bot
```

---

## ⚡ Quick Start

Here's the minimal setup to get a bot responding to `/start`.

### 1. Add the app and configure settings

```python
# settings.py
INSTALLED_APPS = [
    ...
    "dj_telegram_bot.contrib",
]

BOT_TOKEN = "your-telegram-bot-token"
TM_WEBHOOK_URL = "https://api.telegram.org"  # or your local Bot API server (TDLib)
```

### 2. Provide a User model

You must have a user model that inherits from `AbstractUser` and `TelegramUserMixin`, which automatically gives you the `user_id` and `step` fields:

```python
# your_app/models.py
from django.contrib.auth.models import AbstractUser
from dj_telegram_bot.contrib.mixins import TelegramUserMixin

class User(AbstractUser, TelegramUserMixin):
    pass
```

```python
# settings.py
AUTH_USER_MODEL = "your_app.User"
```

You can add any additional fields you need to this model.

### 3. Include the URLs and run migrations

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path("telegram/", include("dj_telegram_bot.contrib.urls")),
]
```

```bash
python manage.py migrate
```

### 4. Set the webhook

Telegram needs to know where to send updates. Call `setWebhook`, pointing it at the `/telegram/webhook/` path from step 3:

```bash
# Official Telegram API (api.telegram.org)
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://yourdomain.com/telegram/webhook/

# Local Bot API server (TDLib)
http://127.0.0.1:8081/bot<BOT_TOKEN>/setWebhook?url=http://127.0.0.1:8000/telegram/webhook/
```

Replace `<BOT_TOKEN>` with your bot token. For the `url` param: if you're using the official Telegram API server, set it to your own public domain; if you're using a local Bot API server (TDLib), set it to your django local ip:port.

### 5. Write a handler

Create a `bot_handlers/` directory inside any of your Django apps — anything you put here is auto-discovered:

```text
your_app/
├── bot_handlers/
│   └── start.py
```

```python
# your_app/bot_handlers/start.py
from dj_telegram_bot.core.handlers import CommandHandler

class StartHandler(CommandHandler):
    @CommandHandler.register("start")
    def start(self):
        self.bot.send_message(chat_id=self.chat_id, text="Hello!")
```

That's it — your bot now replies to `/start`. Keep reading for the full setup.

---

## 🛠 Full Setup

### Settings reference

| Setting          | Required | Description                                                                                      |
| ---------------- | -------- | ------------------------------------------------------------------------------------------------ |
| `BOT_TOKEN`      | Yes      | Bot token obtained from BotFather.                                                               |
| `TM_WEBHOOK_URL` | Yes      | Base URL for the Telegram Bot API — use `https://api.telegram.org` or your local Bot API server. |
| `PROXY_SOCKS`    | No       | SOCKS5 proxy address (`IP:PORT`) for connecting to Telegram.                                     |

### Where to put your handlers

The standard, recommended way is the `bot_handlers/` directory shown in Quick Start.
If you'd rather keep your handlers somewhere else (e.g. inside an existing `views.py`), that's fine too — but that module needs to be imported manually somewhere Django will load it, otherwise the decorators inside it never run. The cleanest place to do this is your app's `apps.py`:

```python
# your_app/apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    name = "your_app"

    def ready(self):
        from . import views  # wherever your handlers live
```

---

## 📝 Usage

<details>
<summary><strong>Messages & keyboards managed from the admin</strong></summary>

Instead of hardcoding text and keyboards, define them in the Django admin (**Messages** section) and fetch them by step. First create a `Message` in the admin with a `step` value (e.g. `"home"`), then reference it in your handler:

```python
from dj_telegram_bot.core.handlers import CommandHandler
from dj_telegram_bot.core.keyboard import KeyboardBuilder
from dj_telegram_bot.contrib.services import MessageService

class HomeHandler(CommandHandler):
    @CommandHandler.register("start")
    def start(self):
        msg = MessageService.get_msg_by_step("home")
        markup = KeyboardBuilder(msg).build()
        self.bot.send_message(chat_id=self.chat_id, text=msg.text, reply_markup=markup)
```

Each `Message` can have an associated `Keyboard` (reply or inline), with fully configurable `Button` rows/columns/data — all editable from the admin panel.

</details>

<details>
<summary><strong>Requiring channel membership before access</strong></summary>

Use the `@sponsor_required` decorator to require users to join specific channels before a handler runs. Channels are configured via the **ChannelSponsor** model in the admin panel.

```python
from dj_telegram_bot.core.handlers import CommandHandler
from dj_telegram_bot.contrib.decorators import sponsor_required

class GatedHandler(CommandHandler):
    @CommandHandler.register("start")
    @sponsor_required
    def start(self):
        ...
```

If the user hasn't joined the required channels, they'll automatically receive a prompt with join links and a confirmation button — your handler only runs after they've joined.

</details>

<details>

<summary><strong>Bot maintenance mode</strong></summary>

Set `BotUpdateStatus.is_update` to `True` (via the admin panel or `BotStatusService.set_updating(True)`) to pause all update processing — useful during deployments or maintenance.

</details>

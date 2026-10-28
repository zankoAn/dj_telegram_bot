---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

# Build your Telegram bots<br>in a Django way.

Decorator routing. Edit messages and keyboards from the admin. Fully typed.

[Get started](getting-started.md){ .md-button .md-button--primary }
[Handlers](handlers.md){ .md-button }

<div class="hero-code" markdown>

```python
from dj_telegram_bot.core.handlers import command_handler

@command_handler("start")
def start(ctx):
    ctx.bot.send_message(ctx.chat_id, "Hello!")
```

</div>

</div>

## Start here

New to the library? Read these three pages in order. Everything else can wait until you need it.

1. **[Getting started](getting-started.md)**: install, connect the webhook and answer `/start`.
2. **[Handlers](handlers.md)**: reply to commands, messages and buttons.
3. **[Examples](examples.md)**: copy a working example for what you are building.

## What's inside

<div class="grid cards" markdown>

- :material-routes:{ .lg .middle } **Decorator routing**

    ---

    Commands, messages, callbacks, inline queries, steps and `*` wildcards. Write functions or classes.

    [:octicons-arrow-right-24: Handlers](handlers.md)

- :material-shield-check:{ .lg .middle } **Built-in guards**

    ---

    `@staff_required`, `@superuser_required`, `@sponsor_required` (make users join your channels first), and `@before_handler` for your own checks.

    [:octicons-arrow-right-24: Access control](access-control.md)

- :material-keyboard:{ .lg .middle } **Edit from the admin**

    ---

    Messages and keyboards live in the database. Build them visually, change them without a redeploy.

    [:octicons-arrow-right-24: Messages & keyboards](admin.md)

- :material-code-braces:{ .lg .middle } **Fully typed**

    ---

    Every Telegram type is a Pydantic model. Autocomplete and type safety everywhere.

    [:octicons-arrow-right-24: Telegram client](bot-api.md)

- :material-wrench-clock:{ .lg .middle } **Maintenance mode**

    ---

    Pause the bot and show a custom message, from the admin or from code.

    [:octicons-arrow-right-24: Before handlers](before-handlers.md)

- :material-account-outline:{ .lg .middle } **Optional user model**

    ---

    Let the bot create users for you, bring your own model, or use none at all.

    [:octicons-arrow-right-24: User model](users.md)

- :material-lan-connect:{ .lg .middle } **Proxy and local server**

    ---

    SOCKS5 proxy and local Bot API server (TDLib) support.

    [:octicons-arrow-right-24: Configuration](configuration.md)

</div>

## How it works

```text
Telegram ──webhook──▶ TelegramWebhookView
                          │
                       Dispatcher        picks a handler class by update type
                          │
                    before handlers      your checks, run on every update
                          │
                   Router.find(...)      exact → step → wildcard
                          │
                     your function or method
```

1. Telegram POSTs an update to `/telegram/webhook/`.
2. The `Dispatcher` wraps it in a handler object for its update type (command, message, callback, inline query or chosen inline result).
3. Every [`@before_handler`](before-handlers.md) runs. If one returns `True`, processing stops.
4. The `Router` looks for a matching route and calls it.

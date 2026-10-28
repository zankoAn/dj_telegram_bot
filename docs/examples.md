# Examples

Short, copy-paste examples for common tasks. Each one links to the page that explains it in full.

!!! tip
    Put these in a file inside `bot_handlers/` (for example `your_app/bot_handlers/shop.py`). See [Getting started](getting-started.md#5-write-your-first-handler).

## The basics

### Handle a command

```python title="bot_handlers/help.py"
from dj_telegram_bot.core.handlers import command_handler

@command_handler("help")
def help_(ctx):
    ctx.bot.send_message(ctx.chat_id, "Send /start to begin.")
```

### Read a command argument

`/start ref_42` is the text `start ref_42`, so match with a wildcard:

```python title="bot_handlers/start.py"
from dj_telegram_bot.core.handlers import command_handler

@command_handler("start*")
def start(ctx):
    payload = ctx.command.removeprefix("start").strip()   # "ref_42", or "" for plain /start
    ctx.bot.send_message(ctx.chat_id, f"Welcome! Referral: {payload or 'none'}")
```

More in [Triggers and wildcards](handlers.md#triggers-and-wildcards).

### Answer a button press

```python title="bot_handlers/shop.py"
from dj_telegram_bot.core.handlers import callback_handler

@callback_handler("buy_*")
def buy(ctx):
    item = ctx.callback_data.removeprefix("buy_")
    ctx.bot.answer_callback_query(ctx.callback_query.id, text=f"Added {item}")
```

Build the buttons themselves in the admin: [Messages & keyboards](admin.md).

### Reply to anything unmatched

```python title="bot_handlers/fallback.py"
from dj_telegram_bot.core.handlers import message_handler

@message_handler("*", priority=-10)   # tried last
def fallback(ctx):
    ctx.bot.send_message(ctx.chat_id, "Sorry, I didn't understand that.")
```

## Conversations

### Ask a question and use the answer

A [step](handlers.md#steps) remembers where the user is in a conversation. This needs a [user model](users.md).

```python title="bot_handlers/register.py"
from dj_telegram_bot.core.handlers import command_handler, message_step_handler

@command_handler("register")
def register(ctx):
    ctx.set_step("ask_name")
    ctx.bot.send_message(ctx.chat_id, "What's your name?")

@message_step_handler("ask_name")
def got_name(ctx):
    ctx.set_step("home")
    ctx.bot.send_message(ctx.chat_id, f"Nice to meet you, {ctx.text}!")
```

### Keep related handlers together

```python title="bot_handlers/shop.py"
from dj_telegram_bot.core.handlers import UpdateHandler, command_handler, callback_handler

class Shop(UpdateHandler):
    @command_handler("shop")
    def open_shop(self):
        self.bot.send_message(self.chat_id, "Welcome to the shop")

    @callback_handler("buy_*")
    def buy(self):
        item = self.callback_data.removeprefix("buy_")
        self.bot.answer_callback_query(self.callback_query.id, text=f"Added {item}")
```

## Access control

### Staff-only command

The guard goes **under** the route decorator. It needs a [user model](users.md) with `is_staff`. For everyone else it stays silent.

```python title="bot_handlers/admin.py"
from dj_telegram_bot.core.guards import staff_required
from dj_telegram_bot.core.handlers import command_handler

@command_handler("stats")
@staff_required
def stats(ctx):
    ctx.bot.send_message(ctx.chat_id, "Staff only!")
```

More in [Access control](access-control.md).

### Require joining a channel

Add the channels in the admin first. Then guard the handler, and handle the confirmation button:

```python title="bot_handlers/start.py"
from dj_telegram_bot.core.guards import SponsorGuard, sponsor_required
from dj_telegram_bot.core.handlers import callback_handler, command_handler

@command_handler("start")
@sponsor_required
def start(ctx):
    ctx.bot.send_message(ctx.chat_id, "Welcome!")

@callback_handler("sponsor_required")
def sponsor_confirmed(ctx):
    if SponsorGuard(ctx).ensure_joined(use_cache=False):
        ctx.bot.send_message(ctx.chat_id, "Thanks, you can use the bot now!")
```

More in [the steps](access-control.md#sponsor_required).

## Inline mode

### Require joining a channel for inline queries

The same guard works for inline queries and for buttons on inline messages. The user gets a default answer, which you can [replace](access-control.md#advanced):

```python title="bot_handlers/search.py"
from dj_telegram_bot.core.guards import sponsor_required
from dj_telegram_bot.core.handlers import inline_handler

@inline_handler("*")
@sponsor_required
def search(ctx):
    ...  # answer the inline query
```

## Before and outside handlers

### Ignore blocked users and pause the bot

Maintenance mode and blocking are opt-in. Register them once:

```python title="bot_handlers/access.py"
from dj_telegram_bot.core.handlers import before_handler

@before_handler
def access(ctx):
    return ctx.is_update_mode() or ctx.is_user_block(notify_user=True)
```

Returning `True` stops the update. More in [Before handlers](before-handlers.md).

### Send a message outside a handler

In a management command or a Celery task there is no `ctx`. Get the shared client instead:

```python title="tasks.py"
from dj_telegram_bot.contrib.services import get_tm_client

bot = get_tm_client()
bot.send_message(chat_id=12345, text="Hello from a task")
```

More in [Telegram client](bot-api.md).
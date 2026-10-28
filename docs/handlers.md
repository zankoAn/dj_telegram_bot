# Handlers

A handler is a function (or a method) that runs when an update matches a trigger. You write it, decorate it with the trigger, and the library does the routing.

```python
from dj_telegram_bot.core.handlers import command_handler

@command_handler("start")
def start(ctx):
    ctx.bot.send_message(ctx.chat_id, "Hello!")
```

`ctx` is the **handler object**: it gives you the bot, the chat, the text, the user and more. The full list is in [Handler object](handler-object.md).

## Pick a decorator

Most bots use `@command_handler`, `@message_handler` and `@callback_handler`. The others cover steps, inline mode and channel posts.

| Decorator | Runs for | Trigger is matched against |
| --- | --- | --- |
| `@command_handler` | messages starting with `/` | the text **without** the leading `/`, including arguments |
| `@message_handler` | every other message, and channel posts | the text (or caption) |
| `@message_step_handler` | same as above | the user's current `step` |
| `@callback_handler` | inline button presses | `callback_data` |
| `@callback_step_handler` | inline button presses | the user's current `step` |
| `@inline_handler` | inline queries | the query text |
| `@chosen_handler` | a chosen inline result | the `result_id` |

??? note "Imports"

    ```python
    from dj_telegram_bot.core.handlers import (
        command_handler,
        message_handler,
        callback_handler,
        inline_handler,
        chosen_handler,
        message_step_handler,
        callback_step_handler,
    )
    ```

## Function or class?

!!! tip
    Start with functions. Reach for a class when you want to keep related handlers together.

### Function handlers

The function receives the handler object, conventionally named `ctx`. Type-hint it to get autocomplete:

```python
from dj_telegram_bot.core.handlers import CommandHandler, command_handler

@command_handler("start")
def start(ctx: CommandHandler):
    ctx.bot.send_message(ctx.chat_id, "Hello!")
```

The class of `ctx` depends on the decorator:

| Decorator | `ctx` is a |
| --- | --- |
| `@command_handler` | `CommandHandler` |
| `@message_handler`, `@message_step_handler` | `MessageHandler` |
| `@callback_handler`, `@callback_step_handler` | `CallBackQueryHandler` |
| `@inline_handler` | `InlineQueryHandler` |
| `@chosen_handler` | `ChosenInlineResultHandler` |

One function can serve several triggers by stacking decorators:

```python
@command_handler("help")
@message_handler("Help")
def help_(ctx):
    ...
```

### Class handlers

Group related handlers in a class. Inherit from `UpdateHandler` and decorate **methods**:

```python
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

`UpdateHandler` has every member of every update type, so your editor shows `self.bot`, `self.chat_id`, `self.callback_data` and the rest in any method.

!!! note
    Members that belong to another update type are empty (`""` or `None`): `self.callback_data` is `""` inside a `@command_handler` method.

!!! note
    The library creates your class as `Shop(update, bot)` when a route matches. If you override `__init__`, keep that signature and call `super().__init__(update, bot)`.

If a class only handles one update type, you can inherit from that class instead (`CallBackQueryHandler`, `CommandHandler`, ...). `BaseHandler` has only the members common to every update.

## Triggers and wildcards

A trigger is an exact string, or a string with `*`:

| Trigger | Matches |
| --- | --- |
| `"start"` | exactly `start` |
| `"buy_*"` | anything starting with `buy_` |
| `"*_done"` | anything ending with `_done` |
| `"*promo*"` | anything containing `promo` |
| `"*"` | everything |

`*` is only allowed at the start, the end, or both. `"a*b"` raises `ValueError` when the module loads.

!!! warning "Command arguments"
    `ctx.command` is the whole text after the slash. `/start` gives `"start"`, but `/start ref_42` gives `"start ref_42"`, and `/start@MyBot` gives `"start@MyBot"`. Use `"start*"` to accept arguments:

    ```python
    @command_handler("start*")
    def start(ctx):
        payload = ctx.command.removeprefix("start").strip()   # "ref_42"
    ```

### Lookup order

For every update the router tries, in this order, and uses the first match:

1. **exact** trigger
2. the user's **step** (message and callback handlers only)
3. **wildcards**, highest `priority` first, then the longest literal part

```python
@message_handler("*", priority=-10)      # fallback, tried last
def fallback(ctx): ...

@message_handler("buy_*")
def buy(ctx): ...

@message_handler("buy_premium_*")        # longer literal, wins over "buy_*"
def buy_premium(ctx): ...
```

!!! warning
    Registering the same trigger twice with different functions logs a warning (`Pattern 'x' in message overridden`) and the last one wins.

## Steps

A step is a short string stored on the user (`user.step`, default `"home"`). It lets you build conversations: ask something, set a step, handle the next message.

```python
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

!!! warning
    Step handlers need a [database user](users.md) with `user_id` and `step` fields. Without one, `user_step` is an empty string and they never match.

- An exact trigger always wins over a step, so a user in `ask_name` who taps a button with an exact handler still reaches that handler.
- Step handlers also fire for non-text messages (photo, contact, location). `ctx.text` is empty in that case.
- `callback_step_handler` does the same for inline button presses.

## Unmatched updates

!!! info
    If nothing matches, the update is silently ignored. Add a `@message_handler("*", priority=-10)` if you want a fallback reply.

## Next

- [Examples](examples.md): working examples you can copy.
- [Handler object](handler-object.md): everything `ctx` / `self` gives you.
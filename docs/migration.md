# Migration guide: 0.1.x → 0.2

The routing layer was rewritten. Most bots need only a few mechanical changes.

!!! info
    The "before" examples come from the 0.1.4 README. If you used other 0.1.x APIs, check them against the [Handlers](handlers.md) page.

!!! tip "The short version"
    Replace `@Class.register(...)` with a decorator, import routing from `dj_telegram_bot.core.handlers`, and register [`@before_handler`](before-handlers.md) checks if you used maintenance mode or blocked users.

## 1. Handlers: `register` → decorators

`HandlerRegistry` was replaced by a `Router`, and `CommandHandler.register(...)` no longer exists. Use decorators directly on your handler methods.

=== "Before (0.1.x)"

    ```python
    from dj_telegram_bot.core.handlers import CommandHandler

    class StartHandler(CommandHandler):
        @CommandHandler.register("start")
        def start(self):
            self.bot.send_message(chat_id=self.chat_id, text="Hello!")
    ```

=== "After (0.2)"

    ```python
    from dj_telegram_bot.core.handlers import CommandHandler, command_handler

    class StartHandler(CommandHandler):
        @command_handler("start")
        def start(self):
            self.bot.send_message(chat_id=self.chat_id, text="Hello!")
    ```

| Update | Decorator |
| --- | --- |
| command | `@command_handler` |
| message | `@message_handler`, `@message_step_handler` |
| callback | `@callback_handler`, `@callback_step_handler` |
| inline query | `@inline_handler` |
| chosen inline result | `@chosen_handler` |

## 2. Imports

Handler classes, every route decorator and `before_handler` are imported from one module, `dj_telegram_bot.core.handlers`:

```python
from dj_telegram_bot.core.handlers import (
    UpdateHandler,
    before_handler,
    command_handler,
    message_handler,
    callback_handler,
)
```

The routing code lives in `core/routing.py`, but that module is internal. Don't import from it.

`sponsor_required` moved from `contrib.decorators` to `core.guards`:

```diff
- from dj_telegram_bot.contrib.decorators import sponsor_required
+ from dj_telegram_bot.core.guards import sponsor_required
```

## 3. Maintenance mode and user blocking are optional

In 0.1.x these checks ran automatically. Now you register them as [before handlers](before-handlers.md). To keep the old behavior, including the reply to blocked users:

```python
from dj_telegram_bot.core.handlers import before_handler

@before_handler
def check_user_and_bot_status(ctx):
    return ctx.is_update_mode() or ctx.is_user_block(notify_user=True)
```

Without these, blocked users and maintenance mode have **no effect**.

## 4. Sponsor confirmation button

Handle the `sponsor_required` callback, see [Access control](access-control.md#3-handle-the-confirmation-button).

## Behavior changes

| Change | Action |
| --- | --- |
| Maintenance mode applies to private chats only | none, unless you relied on it in groups |
| `is_user_block()` stays silent unless you pass `notify_user=True` | pass it to keep the reply |
| Blocked users are ignored in every chat type, not just private | none |
| Database users are created only in private chats. In groups and inline mode they are only looked up, and there is no `typing` chat action | none; `ctx.user_obj` can now be `None`, so check `ctx.has_started_bot` |
| `ctx.user` is `None` for channel posts (it used to be the channel) | use `ctx.sender` |
| `ChosenInlineResultHandler.query` is now `chosen_query`. `query` is the inline query text | rename the attribute |
| `SponsorGuard.enforce()` is now `ensure_joined()`; `enforce` still works | none |
| The sponsor check is skipped in groups and for channel posts | none, unless you relied on it in groups |
| New users get their Telegram id as password. In 0.1.x it was unusable | [set a real password before `is_staff`](users.md#what-gets-filled-in), or override creation |
| Link previews are disabled by default in `send_message` | pass `link_preview_options=LinkPreviewOptions(is_disabled=False)` to restore |
| `AUTH_USER_MODEL` is optional; the startup check for `TelegramUserMixin` is gone | none |
| In methods that take `business_connection_id`, it is no longer the first parameter. `edit_message_text` now takes `chat_id`, `message_id`, `text` in that order | pass arguments by keyword; a positional call can silently send the wrong value |
| Telegram types follow the newer Bot API, so some fields changed or were added | re-run your type checker |

## New features worth adopting

- [`UpdateHandler`](handlers.md#class-handlers) as the one class to inherit from, and one import path for routing: `dj_telegram_bot.core.handlers`
- [`@before_handler`](before-handlers.md) for your own pre-routing checks, including [a channel membership check for every update](before-handlers.md#channel-membership-for-every-update)
- [Your own user model](users.md), and `get_or_create_telegram_user()` to customize creation
- `ctx.has_started_bot` and `ctx.sender`
- [`@staff_required` and `@superuser_required`](access-control.md)
- [Step handlers](handlers.md#steps) and `ctx.set_step()`
- [Channel posts and chosen inline results](handlers.md#pick-a-decorator)
- Wildcard `priority`
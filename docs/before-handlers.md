# Before handlers

A before handler runs on **every** update, before routing. Return `True` to stop: no route is looked up and no handler runs.

```python title="bot_handlers/access.py"
from dj_telegram_bot.core.handlers import before_handler

@before_handler
def ignore_banned(ctx):
    return ctx.user_id in BANNED_IDS
```

OR


```python
from dj_telegram_bot.core.handlers import UpdateHandler, before_handler

class Guards(UpdateHandler):
    @before_handler
    def check(self):
        return self.is_user_block()
```
Rules:

- They run in registration order and stop at the first one that returns `True`.
- They run for every update type, even when no route would match.
- `ctx` is an `UpdateHandler`, so every member is available whatever the update type. See [Handler object](handler-object.md).
- The database user is loaded before they run, so `ctx.user_obj` costs nothing extra.
- Returning `False` or `None` lets the update continue.
- Registering the same function twice is ignored.

!!! warning "Errors stop the whole update"
    If a before handler raises, the update is dropped and the error is only logged. Keep them small.

!!! tip "`user_obj` can raise or be `None`"
    `ctx.user_obj` raises `ImproperlyConfigured` if your user model has no `user_id` and `step` fields, and is `None` for someone who never started the bot. In a check that must work everywhere, use `ctx.user_id`. See [User model](users.md).

!!! warning "Built-in checks are not automatic"
    The library gives you two checks, `is_update_mode()` and `is_user_block()`, but does **not** run them for you. Register the ones you need, as shown below.

## Maintenance mode

`ctx.is_update_mode()` returns `True` while the bot is paused and sends the configured message.

```python title="bot_handlers/access.py"
@before_handler
def maintenance(ctx):
    return ctx.is_update_mode()
```

Rules:

- It only applies in **private chats**. Updates from groups, channels and inline mode pass through, so the bot does not spam the message there.
- Superusers are never blocked, so you can test in production.

Turn it on from the admin (**Bot update status**: `is_update` and `update_msg`) or from code:

```python
from dj_telegram_bot.contrib.services import BotStatusService

BotStatusService.set_updating(True)
```

!!! note
    The status is cached for 60 seconds. `set_updating()` clears the cache immediately, but a change made in the admin can take up to a minute to apply.

## Blocked users

Set `is_active = False` on a user to block them, then register:

```python title="bot_handlers/access.py"
@before_handler
def blocked(ctx):
    return ctx.is_user_block(notify_user=True)
```

`is_user_block()` returns `True` for a blocked user in **every** chat type, so the bot stays silent in groups and inline mode too. It only **replies** when you pass `notify_user=True` and the update comes from a private chat. The default is `notify_user=False`: the user is ignored without a reply.

The reply is the message with step `block` from the admin ([Messages & keyboards](admin.md)), or the built-in text `Access denied. Your account is currently blocked`.

This check reads `is_active` on your user model. See [User model](users.md#with-your-own-model).

!!! tip "Use both checks"
    ```python
    @before_handler
    def access(ctx):
        return ctx.is_update_mode() or ctx.is_user_block(notify_user=True)
    ```

## Channel membership for every update

`@sponsor_required` guards one handler. To require channel membership for **every** update, use the guard in a before handler.

```python title="bot_handlers/access.py"
from dj_telegram_bot.core.guards import SponsorGuard

@before_handler
def sponsor(ctx):
    return not SponsorGuard(ctx).ensure_joined()
```

!!! warning "Note the `not`"
    `ensure_joined()` returns `True` when the user may continue, while a before handler returns `True` to stop.

The same [rules](access-control.md#where-it-applies) apply: groups and channel posts are skipped. You do not also need `@sponsor_required` on the handlers.

## Order matters

!!! tip
    Put cheap checks first and register the ones with side effects (like sending a message) after the checks that should win. Registration order follows module import order.
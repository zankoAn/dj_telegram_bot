# Access control

Guards decide whether a handler runs. Put them **under** the route decorator.

| Decorator | Lets the update through when | When blocked |
| --- | --- | --- |
| [`@sponsor_required`](#sponsor_required) | the user joined every sponsor channel | sends a join prompt |
| [`@staff_required`](#staff_required-and-superuser_required) | the database user has `is_staff` | silent |
| [`@superuser_required`](#staff_required-and-superuser_required) | the database user has `is_superuser` | silent |

```python
from dj_telegram_bot.core.guards import sponsor_required, staff_required
from dj_telegram_bot.core.handlers import command_handler

@command_handler("stats")
@staff_required
def stats(ctx):
    ...
```

!!! tip
    When a guard blocks the update, the handler does not run and the guard returns `False`.

## `@staff_required` and `@superuser_required`

They check the flag on the database user, so they need a [user model](users.md). They also block when there is no database user.

They are **silent**: the user gets no reply. To send a message, use [`@before_handler`](before-handlers.md) or check `ctx.user_obj.is_staff` inside the handler.

## `@sponsor_required`

Force users to join one or more channels before the handler runs.

### 1. Add the channels

In the admin, open **Channel sponsors** and add:

| Field | Meaning |
| --- | --- |
| `name` | button label |
| `chat_id` | channel id; the `-100` prefix is added automatically |
| `link` | invite or public link shown on the button |
| `is_active` | only active channels are checked |

!!! warning
    Add your bot as an **administrator** of each channel. Otherwise Telegram will not let it check membership.

### 2. Decorate the handler

```python
@command_handler("start")
@sponsor_required
def start(ctx):
    ctx.bot.send_message(ctx.chat_id, "Welcome!")
```

If the user has not joined every active channel, they get a prompt with one button per channel and a confirmation button. The handler does not run.

### 3. Handle the confirmation button

The confirmation button sends `callback_data="sponsor_required"`. Register a handler for it:

```python
from dj_telegram_bot.core.guards import SponsorGuard
from dj_telegram_bot.core.handlers import callback_handler

@callback_handler("sponsor_required")
def sponsor_confirmed(ctx):
    if SponsorGuard(ctx).ensure_joined(use_cache=False):
        ctx.bot.send_message(ctx.chat_id, "Thanks, you can use the bot now!")
```

`ensure_joined()` returns `True` if the user joined every channel. Otherwise it sends the prompt again and returns `False`.

### Where it applies

| Update | Checked? |
| --- | --- |
| private chat | yes |
| group, supergroup | no |
| channel post | no |
| inline query | yes |
| button on an inline message | yes |

Results are cached for 60 seconds per user and channel.

### Texts

Texts come from [Messages](admin.md) with these steps. English defaults are used if a message is missing.

| `related_step` | Used for | Default |
| --- | --- | --- |
| `sponsor-prompt-text` | the prompt message | `To use the bot, please join the channels below.` |
| `sponsor-submit-text` | confirmation button label | `Confirm membership ✅` |
| `sponsor-join-error` | inline answers and callback alerts | `Please join the sponsor channels first, then try again.` |

### Advanced

??? note "Customize inline answers"

    Inline queries and buttons on inline messages have no chat to send a prompt to, so the guard answers with an article (inline query) or an alert (button). To replace these answers, pass a function that receives the handler context and the channels the user has not joined:

    ```python
    def join_first_inline(ctx, channels):
        ...  # answer the inline query yourself

    def join_first_callback(ctx, channels):
        ...  # answer a button press on an inline message

    @inline_handler("*")
    @sponsor_required(on_inline=join_first_inline)
    def search(ctx):
        ...

    @callback_handler("like:*")
    @sponsor_required(on_callback=join_first_callback)
    def like(ctx):
        ...
    ```

    Pass only what you need: an argument you leave out keeps the default answer. `@sponsor_required` without arguments still works.

    !!! note
        Telegram limits an alert text to 200 characters.

??? note "Check every update"

    To check every update instead of single handlers, use the guard in a [before handler](before-handlers.md#channel-membership-for-every-update).

??? note "Use the guard directly"

    ```python
    guard = SponsorGuard(ctx)
    missing = guard.get_not_joined(use_cache=False)   # list of ChannelSponsor
    allowed = guard.ensure_joined()                  # True, or sends the prompt
    ```
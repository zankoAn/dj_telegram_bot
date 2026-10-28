# Handler object

This page is a reference. You do not need to read it top to bottom: come here when you want to know what `ctx` (in a function handler) or `self` (in a class handler) can do.

## On every handler

| Member | Description |
| --- | --- |
| `bot` | the [Telegram client](bot-api.md) |
| `update` | the raw `Update` |
| `text` | message text or caption (`""` if none) |
| `message` | the message (for a callback, the message the button belongs to) |
| `callback_query`, `inline_query`, `chosen` | the matching part of the update, or `None` |
| `query` | the inline query text (`""` if none) |
| `inline_message_id` | set for buttons on inline messages |
| `chat`, `chat_id` | where to answer (`chat_id` is `0` if there is no chat) |
| `user`, `user_id` | the Telegram user who sent the update (`None` and `0` for channel posts) |
| `sender` | the user, or for channel posts the sender chat or the channel |
| `is_private()`, `is_group()`, `is_inline_callback()` | where the update came from |
| `has_joined_channel(chat_id, user_id)` | membership check |
| `is_update_mode()`, `is_user_block()` | the [built-in checks](before-handlers.md) |

!!! note "Groups, channels and inline updates"
    For channel posts there is no `user`: use `sender`. For buttons on inline messages `chat` is the user themselves, because the real chat is unknown. Database users are created only in private chats; see [User model](users.md#when-users-are-created).

!!! info "`is_private()`"
    `is_private()` is `True` for private chats. For inline queries it follows the query's `chat_type`, and for buttons on inline messages it is always `False`, because the real location is unknown.

## The database user

See [User model](users.md) for how to set it up.

| Member | Description |
| --- | --- |
| `user_obj` | your database user, or `None` |
| `has_started_bot` | `True` if a database user exists |
| `user_step` | the current step, or `""` |
| `set_step(step)` | save a new step on the database user |

## Per update type

These also exist on `UpdateHandler`.

| Member | Class | Description |
| --- | --- | --- |
| `command` | `CommandHandler` | text without the leading `/` (`""` if not a command) |
| `callback_data` | `CallBackQueryHandler` | the button's `callback_data` |
| `result_id` | `ChosenInlineResultHandler` | the chosen result's id |
| `chosen_query` | `ChosenInlineResultHandler` | the query typed before the result was chosen |
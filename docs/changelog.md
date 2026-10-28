# Changelog

## 0.2.0 (2026-10-28)

### Breaking

- `HandlerRegistry` and `CommandHandler.register(...)` replaced by decorators: `@command_handler`, `@message_handler`, `@callback_handler`, `@inline_handler`, `@chosen_handler`. Import them, and the handler classes, from `dj_telegram_bot.core.handlers`. The routing code (`core/routing.py`) is internal
- Maintenance mode and blocked-user checks no longer run automatically. Register them with `@before_handler`
- `is_user_block()` replies only with `notify_user=True`
- `ctx.user` is `None` for channel posts. Use `ctx.sender`
- `ChosenInlineResultHandler.query` renamed to `chosen_query`
- Access guards (`sponsor_required`, `SponsorGuard`, and the new `staff_required` and `superuser_required`) live in `dj_telegram_bot.core.guards`. `sponsor_required` used to be in `contrib.decorators`
- Link previews are disabled by default in `send_message`
- New users get their Telegram id as password (was unusable)
- `business_connection_id` moved after the main parameters in the business and edit methods (`edit_message_text` is now `chat_id, message_id, text`). Use keyword arguments

See the [migration guide](migration.md).

### Added

- One import path: handler classes, all route decorators and `@before_handler` come from `dj_telegram_bot.core.handlers`
- `UpdateHandler`: one class with every member of every update type, to inherit from in class handlers. Each update type also has its own class (`CommandHandler`, `MessageHandler`, `CallBackQueryHandler`, `InlineQueryHandler`, `ChosenInlineResultHandler`) with only its own members.
- `@before_handler` for pre-routing checks, as functions or class methods; registering a function twice is ignored. See [Before handlers](before-handlers.md)
- Optional user model: any model with `user_id` and `step` works, and `TelegramUserMixin.get_or_create_telegram_user()` customizes creation. See [User model](users.md)
- `ctx.sender`, `ctx.has_started_bot`, `ctx.chosen`
- `SponsorGuard.ensure_joined()`, usable in a before handler for every update
- `@staff_required` and `@superuser_required`
- Step handlers: `@message_step_handler`, `@callback_step_handler`, and `set_step()`
- Wildcard triggers with `priority`
- `ChosenInlineResultHandler` and `@chosen_handler`
- Channel post support 
- Inline queries and inline callbacks in the sponsor check. Customize the answers with `@sponsor_required(on_inline=..., on_callback=...)`
- `switch_inline_query_current_chat` in the keyboard builder
- Telegram Bot API updates: February to July 2026, up to 10.3

### Changed

- Database users are created only in private chats; elsewhere they are only looked up. The `typing` chat action in groups is gone
- Maintenance mode applies to private chats only
- The sponsor check is skipped in groups and channels
- `AUTH_USER_MODEL` is optional; the startup check for `TelegramUserMixin` is removed
- Membership logic moved into `SponsorGuard`; `enforce()` stays as an alias of `ensure_joined()`

### Fixed

- Callbacks from inline messages
- Chat and user resolution for inline and group updates
- File name used for cover uploads
- Shared mutable default in `_add_file`

## 0.1.4

Last release before the router rewrite.
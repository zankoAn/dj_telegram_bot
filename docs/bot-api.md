# Telegram client

Inside a handler, `ctx.bot` is a typed client for the Bot API. Outside a handler (a management command, a Celery task), get the same shared client with:

```python
from dj_telegram_bot.contrib.services import get_tm_client

bot = get_tm_client()
bot.send_message(chat_id=12345, text="Hello from a task")
```

## Calling methods

Methods mirror the Bot API in `snake_case` and return Pydantic models:

```python
msg = ctx.bot.send_message(chat_id=ctx.chat_id, text="<b>Hi</b>")
print(msg.message_id)

ctx.bot.send_photo(ctx.chat_id, photo="https://example.com/cat.jpg", caption="A cat")
ctx.bot.edit_message_text(...)
ctx.bot.answer_callback_query(ctx.callback_query.id, text="Done", show_alert=True)
```

Every Telegram type lives in `dj_telegram_bot.core.types`.

## Defaults

| Setting | Default |
|---|---|
| `parse_mode` | `"html"` in most methods |
| Link previews in `send_message` | disabled |

## Files

Methods that upload media accept any of the following:

| Type | Example |
|---|---|
| `str` | a `file_id` or an HTTP URL |
| `bytes` | raw file content |
| File object | `open("photo.jpg", "rb")` |

## Errors

Telegram errors raise `TelegramAPIError`, a subclass of `TelegramError`:

```python
from dj_telegram_bot.core.exceptions import TelegramAPIError

try:
    ctx.bot.send_message(chat_id, "hi")
except TelegramAPIError as e:
    print(e.method, e.error_code, e.description)
```

Network failures and invalid responses raise the same exception with `error_code == 0`.

## Good to know

- **Synchronous:** the client is built on `requests`, with a 30 second timeout (100 seconds when uploading files).
- **Cached:** it is cached with `lru_cache`, so one client is shared per process.
- **Proxy and local server:** configured with [`PROXY_SOCKS` and `TM_WEBHOOK_URL`](configuration.md).
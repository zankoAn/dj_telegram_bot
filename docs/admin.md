# Messages & keyboards

Keep texts and keyboards in the database so you can change them from the Django admin without redeploying.

## Create a message

In the admin, open **Messages**:

- `text`: the message text (HTML is the default parse mode)
- `related_step`: the key you use to fetch it, for example `home`

Below the text there is a visual keyboard builder. A message can have one keyboard:

| Field | Meaning |
| --- | --- |
| Type | `REPLY` (reply keyboard) or `INLINE` |
| `resize_keyboard`, `one_time_keyboard` | reply keyboard options |
| Buttons | text, row, column and the button data below |

Button data (all optional): `url`, `callback_data`, `copy_text`, `style`, `request_contact`, `request_location`, `web_app`, `login_url`, `switch_inline_query_current_chat`.

## Send it

```python
from dj_telegram_bot.contrib.services import MessageService
from dj_telegram_bot.core.handlers import command_handler
from dj_telegram_bot.core.keyboard import KeyboardBuilder

@command_handler("start")
def start(ctx):
    msg = MessageService.get_msg_by_step("home")
    markup = KeyboardBuilder(msg).build()
    ctx.bot.send_message(ctx.chat_id, msg.text, reply_markup=markup)
```

## Options the admin cannot store

Some button options cannot live in the admin JSON (`switch_inline_query`, `pay`, `request_poll`, `request_users`, ...). Pass an override for **one** button, identified by its row and column:

```python
from dj_telegram_bot.core.types import InlineButtonOverride

markup = KeyboardBuilder(msg).build(
    override_inline=InlineButtonOverride(row=1, column=2, switch_inline_query="cats")
)
```

For reply keyboards use `override_reply=ReplyButtonOverride(row=..., column=..., request_poll=...)`.

## Messages the library reads for you

| `related_step` | Used by |
| --- | --- |
| `block` | [blocked users](before-handlers.md#blocked-users), when you call `is_user_block(notify_user=True)` |
| `sponsor-prompt-text` | [sponsor prompt](access-control.md#texts) |
| `sponsor-submit-text` | [sponsor confirmation button](access-control.md#texts) |
| `sponsor-join-error` | [sponsor inline errors](access-control.md#texts) |

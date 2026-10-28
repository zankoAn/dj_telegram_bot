# User model

`dj_telegram_bot` can keep a database row for every Telegram user. It is used for [steps](handlers.md#steps), blocking users, and staff checks. A user model is **optional**.

## Three ways to set it up

| Your `AUTH_USER_MODEL` | Users are | `user_obj`, steps, blocking |
| --- | --- | --- |
| inherits `TelegramUserMixin` | **created** for you | work |
| has real `user_id` and `step` fields, no mixin | only **looked up**, never created | work for users you created yourself |
| neither (for example Django's default `User`) | not used | `user_obj` raises `ImproperlyConfigured`; steps never match; blocking does nothing |

!!! note
    "Real" means a normal field, not a relation. A `ForeignKey` named `user` creates a `user_id` attribute, but it does not count.

## With `TelegramUserMixin`

```python title="your_app/models.py"
from django.contrib.auth.models import AbstractUser
from dj_telegram_bot.contrib.mixins import TelegramUserMixin

class User(AbstractUser, TelegramUserMixin):
    pass
```

```python title="settings.py"
AUTH_USER_MODEL = "your_app.User"
```

The mixin adds two fields, so run `makemigrations` and `migrate`:

| Field | Type |
| --- | --- |
| `user_id` | `BigIntegerField`, unique: the Telegram user id |
| `step` | `CharField(max_length=30)`, default `"home"` |

### When users are created

Users are created only in **private chats**: the first time someone writes to the bot. Everywhere else (groups, channels, inline messages) the bot only looks the user up, so `ctx.user_obj` is `None` for someone who never started the bot.

Use `ctx.has_started_bot` to ask whether a database user exists.

### What gets filled in

`get_or_create_telegram_user()` fills only the fields your model has:

| Field | Value |
| --- | --- |
| `username` | the Telegram username, or the user id |
| `first_name` | the Telegram first name |
| `last_name` | the Telegram last name, or `""` |
| `password` | the Telegram user id, hashed |


## With your own model

Skip the mixin and add the two fields yourself:

```python title="your_app/models.py"
user_id = models.BigIntegerField(unique=True)
step = models.CharField(max_length=30, default="home")
```

The bot never creates these users. Create them yourself, for example in `/start`:

```python title="bot_handlers/start.py"
from django.contrib.auth import get_user_model
from dj_telegram_bot.core.handlers import command_handler

User = get_user_model()

@command_handler("start")
def start(ctx):
    User.objects.get_or_create(
        user_id=ctx.user_id,
        defaults={"username": str(ctx.user_id)},
    )
    ctx.bot.send_message(ctx.chat_id, "Welcome!")
```

!!! info
    Two built-in checks read standard fields: `is_user_block()` reads `is_active`, and `is_update_mode()` reads `is_superuser`. Models based on `AbstractUser` have both.

## Using the user

| Member | What it is |
| --- | --- |
| `ctx.user` | the Telegram `User` who sent the update |
| `ctx.user_id` | its id (`0` if the update has no user) |
| `ctx.user_obj` | your database user, or `None` if there is none |
| `ctx.has_started_bot` | `True` if a database user exists |
| `ctx.user_step` | the current step, or `""` |
| `ctx.set_step(step)` | save a new step |

```python title="bot_handlers/profile.py"
@command_handler("profile")
def profile(ctx):
    user = ctx.user_obj
    if user is None:
        return ctx.bot.send_message(ctx.chat_id, "Send /start first.")

    ctx.bot.send_message(ctx.chat_id, f"Your step: {user.step}")
```

!!! warning
    `user_obj` raises `ImproperlyConfigured` when your model has no `user_id` and `step` fields. In that case use `ctx.user_id`.

    `set_step()` raises `LookupError` if there is no database user.

## Customizing creation

Override `get_or_create_telegram_user()` on your model. It receives the Telegram `User` and must return a model instance.

=== "Add your own fields"

    ```python title="your_app/models.py"
    class User(AbstractUser, TelegramUserMixin):
        language = models.CharField(max_length=5, default="en")

        @classmethod
        def get_or_create_telegram_user(cls, tg_user):
            user, _ = cls.objects.get_or_create(
                user_id=tg_user.id,
                defaults={
                    "username": tg_user.username or str(tg_user.id),
                    "first_name": tg_user.first_name,
                    "language": tg_user.language_code or "en",
                },
            )
            return user
    ```

=== "Unusable password"

    ```python title="your_app/models.py"
        @classmethod
        def get_or_create_telegram_user(cls, tg_user):
            user, created = cls.objects.get_or_create(
                user_id=tg_user.id,
                defaults={"username": tg_user.username or str(tg_user.id)},
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])

            return user
    ```

!!! warning
    If your model has a required field the default cannot fill (for example an `email` without a default), creation fails with an `IntegrityError`. Override the method as above.
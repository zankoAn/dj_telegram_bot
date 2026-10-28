from __future__ import annotations

__all__ = [
    # classes
    "UpdateHandler",
    "BaseHandler",
    "CommandHandler",
    "MessageHandler",
    "CallBackQueryHandler",
    "InlineQueryHandler",
    "ChosenInlineResultHandler",
    # decorators
    "command_handler",
    "message_handler",
    "message_step_handler",
    "callback_handler",
    "callback_step_handler",
    "inline_handler",
    "chosen_handler",
    "before_handler",
    # advanced
    "Router",
]


from functools import lru_cache
from typing import Any, ClassVar, cast

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.utils.functional import cached_property

from dj_telegram_bot.contrib.mixins import TelegramUserMixin
from dj_telegram_bot.contrib.services import BotStatusService, MessageService
from dj_telegram_bot.core.routing import (
    Route,
    Router,
    before_handler,
    callback_handler,
    callback_step_handler,
    chosen_handler,
    command_handler,
    default_router,
    inline_handler,
    message_handler,
    message_step_handler,
)
from dj_telegram_bot.core.telegram import Telegram
from dj_telegram_bot.core.types import (
    CallbackQuery,
    Chat,
    ChosenInlineResult,
    InlineQuery,
    Message,
    Update,
    User,
)


@lru_cache()
def user_model_supported(model) -> bool:
    """True if the model uses the mixin, or has real `user_id` and `step` fields."""

    if issubclass(model, TelegramUserMixin):
        return True

    for name in ("user_id", "step"):
        try:
            if model._meta.get_field(name).is_relation:
                return False
        except FieldDoesNotExist:
            return False

    return True


class BaseHandler:
    """
    Base handler class that provides common utilities for processing Telegram updates,
    such as accessing user, chat, and message details.
    """

    handler_type: ClassVar[str | None] = None
    key_attribute: ClassVar[str | None] = None
    uses_step: ClassVar[bool] = False
    router: ClassVar[Router] = default_router

    def __init__(self, update: Update, bot: Telegram):
        self.update = update
        self.bot = bot

    @property
    def inline_query(self) -> InlineQuery:
        return cast(InlineQuery, self.update.inline_query)

    @property
    def callback_query(self) -> CallbackQuery:
        return cast(CallbackQuery, self.update.callback_query)

    @property
    def query(self) -> str:
        return self.inline_query.query if self.inline_query else ""

    @property
    def message(self) -> Message:
        cq = self.callback_query
        if cq and isinstance(cq.message, Message):
            return cast(Message, cq.message)

        return cast(Message, self.update.message)

    @property
    def text(self) -> str:
        message = self.message or self.update.channel_post
        if not message:
            return ""

        return message.text or message.caption or ""

    @property
    def chat(self) -> Chat:
        """
        Returns the chat object from the update, if available.
        """
        cq = self.callback_query
        if cq and cq.message:
            return cast(Chat, cq.message.chat)

        if cq and cq.inline_message_id:
            return cast(Chat, cq.from_user)

        if self.inline_query and self.inline_query.id:
            return cast(Chat, self.inline_query.from_user)

        if self.update.message:
            return cast(Chat, self.update.message.chat)

        if self.update.channel_post:
            return self.update.channel_post.chat

        return cast(Chat, None)

    @property
    def chosen(self) -> ChosenInlineResult | None:
        return self.update.chosen_inline_result

    @property
    def user(self) -> User | None:
        """
        Returns the user object who sent the update, if available.
        """
        update = self.update

        if cq := update.callback_query:
            return cq.from_user

        if iq := update.inline_query:
            return iq.from_user

        if chosen := update.chosen_inline_result:
            return chosen.from_user

        if msg := update.message:
            return msg.from_user

        return None

    @property
    def user_id(self) -> int:
        return self.user.id if self.user else 0

    @property
    def sender(self) -> User | Chat | None:
        if self.user:
            return self.user

        if post := self.update.channel_post:
            return post.sender_chat or post.chat

        return None

    @property
    def chat_id(self) -> int:
        return self.chat.id if self.chat else 0

    @property
    def inline_message_id(self) -> str | None:
        cq = self.update.callback_query
        return cq.inline_message_id if cq else None

    @cached_property
    def _db_user(self):
        """Internal: the DB user, or None (no user in the update, or unsupported model)."""
        user = self.sender
        model = get_user_model()
        if not user or not user_model_supported(model):
            return None

        if self.is_private() and issubclass(model, TelegramUserMixin):
            return model.get_or_create_telegram_user(user)

        return model.objects.filter(user_id=user.id).first()

    @property
    def user_obj(self):
        if not user_model_supported(get_user_model()):
            raise ImproperlyConfigured(
                "user_obj needs `user_id` and `step` fields on your AUTH_USER_MODEL. "
                "Inherit from `TelegramUserMixin` or add them yourself."
            )

        return self._db_user

    def set_step(self, step: str) -> None:
        user = self.user_obj
        if user is None:
            raise LookupError("No database user found for this update.")

        user.step = step
        user.save(update_fields=["step"])

    @property
    def user_step(self) -> str:
        return self._db_user.step if self._db_user else ""

    def is_private(self) -> bool:
        if self.is_inline_callback():
            # location is unknown (could be a group or someone else's chat)
            return False

        if self.inline_query and self.inline_query.from_user:
            return self.inline_query.chat_type == "private"

        if self.chat:
            return self.chat.type == "private"

        return False

    def is_group(self) -> bool:
        if self.chat:
            return self.chat.type in ("supergroup", "group")

        return False

    def is_update_mode(self):
        user = self._db_user
        if user and user.is_superuser:
            return False

        status = BotStatusService.get_status()
        if not status.is_update:
            return False

        if self.is_private():  # no message in groups: it would be spam
            self.bot.send_message(self.chat_id, text=status.update_msg)

        return True

    def is_user_block(self, notify_user=False):
        user = self._db_user
        if not user or user.is_active:
            return False

        if self.is_private() and notify_user:
            msg = MessageService.get_msg_by_step("block")
            self.bot.send_message(
                self.chat_id,
                text=msg.text
                if msg
                else "Access denied. Your account is currently blocked",
            )

        return True

    def is_inline_callback(self) -> bool:
        return bool(self.inline_message_id)

    def has_joined_channel(self, chat_id, user_id):
        chat_id = str(chat_id)
        if chat_id.lstrip("-").isdigit():
            chat_id = int(chat_id)
        else:
            chat_id = chat_id if "@" in chat_id else "@" + chat_id

        rsp = self.bot.get_chat_member(chat_id, user_id)
        return rsp.status != "left"

    @property
    def has_started_bot(self) -> bool:
        return self._db_user is not None

    def _rebuild_as_class(self, cls: type[BaseHandler]) -> BaseHandler:
        """Create a new handler instance of the given class for the current update.

        Passes the update, bot and already-loaded database user to the new instance,
        which avoids a second database query.
        """
        other = cls(self.update, self.bot)
        other.__dict__["_db_user"] = self._db_user
        return other

    def _execute(self, route: Route) -> Any:
        owner, name = route.owner, route.name
        if owner is None or name is None:  # is plain function
            return route.func(self)

        inst = self if isinstance(self, owner) else self._rebuild_as_class(owner)

        return getattr(inst, name)()

    def handle(self) -> bool:
        self._db_user  # load/create the user before any before_handler runs

        if self.router.before:
            full = (
                self
                if isinstance(self, UpdateHandler)
                else self._rebuild_as_class(UpdateHandler)
            )
            if any(check(full) for check in self.router.before):
                return True

        if not self.handler_type or not self.key_attribute:
            return False

        key = getattr(self, self.key_attribute, None)
        if key is None:
            return False

        step = self.user_step if self.uses_step else ""
        route = self.router.find(self.handler_type, key, step)
        if not route:
            return False

        self._execute(route)
        return True


class CommandHandler(BaseHandler):
    handler_type = "command"
    key_attribute = "command"

    @property
    def command(self) -> str:
        if self.text.startswith("/"):
            return self.text.lstrip("/")

        return ""


class MessageHandler(BaseHandler):
    handler_type = "message"
    key_attribute = "text"
    uses_step = True


class CallBackQueryHandler(BaseHandler):
    handler_type = "callback"
    key_attribute = "callback_data"
    uses_step = True

    @property
    def callback_data(self) -> str:
        return str(self.callback_query.data) if self.callback_query else ""


class InlineQueryHandler(BaseHandler):
    handler_type = "inline"
    key_attribute = "query"


class ChosenInlineResultHandler(BaseHandler):
    handler_type = "chosen"
    key_attribute = "result_id"

    @property
    def result_id(self) -> str:
        return self.chosen.result_id if self.chosen else ""

    @property
    def chosen_query(self) -> str:
        return self.chosen.query if self.chosen else ""


class UpdateHandler(
    CommandHandler,
    MessageHandler,
    CallBackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
):
    """All update types in one class: inherit from this to write your handlers."""

    handler_type = None
    key_attribute = None

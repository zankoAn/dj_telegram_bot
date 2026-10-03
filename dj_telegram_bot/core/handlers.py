from __future__ import annotations

from typing import Any, ClassVar, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils.functional import cached_property

from dj_telegram_bot.contrib.services import BotStatusService, MessageService

# Re-exported for backward compatibility
from dj_telegram_bot.core.routing import (  # noqa: F401
    Route,
    Router,
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
    InlineQuery,
    Message,
    Update,
    User,
)

UserDB = get_user_model()


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
    def callback_data(self) -> str:
        return str(self.callback_query.data) if self.callback_query else ""

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
        text = self.message.text if self.message and self.message.text else ""
        return text

    @property
    def command(self) -> str:
        if self.text.startswith("/"):
            return self.text.lstrip("/")

        return ""

    @property
    def chat(self) -> Chat:
        """
        Returns the chat object from the update, if available.
        """
        cq = self.callback_query
        if cq and cq.message:
            return cast(Chat, cq.message.chat)

        if self.inline_query and self.inline_query.id:
            return cast(Chat, self.inline_query.from_user)

        if self.update.message:
            return cast(Chat, self.update.message.chat)

        return cast(Chat, None)

    @property
    def user(self) -> User:
        """
        Returns the user object who sent the update, if available.
        """
        user = None
        if self.message:
            user = self.message.from_user

        if self.callback_query:
            user = self.callback_query.from_user

        if self.inline_query:
            user = self.inline_query.from_user

        return cast(User, user)

    @property
    def user_id(self) -> int:
        return self.user.id if self.user else 0

    @property
    def chat_id(self) -> int:
        return self.chat.id if self.chat else 0

    @cached_property
    def user_obj(self) -> UserDB:
        if not self.user:
            return cast(UserDB, None)

        if not self.is_private():
            try:
                self.bot.send_chat_action(self.chat_id, "typing")
            except Exception:
                return cast(UserDB, None)

        user, _ = UserDB.objects.get_or_create(
            user_id=self.user_id,
            defaults={
                "username": self.user.username or str(self.user_id),
                "password": make_password(str(self.user_id)),
                "first_name": self.user.first_name,
                "last_name": self.user.last_name or str(self.user_id),
            },
        )
        return user

    @property
    def user_step(self) -> str:
        return self.user_obj.step if self.user_obj else ""

    def is_private(self) -> bool:
        if self.inline_query and self.inline_query.from_user:
            return self.inline_query.chat_type in ["private", "sender"]

        if self.chat:
            return self.chat.type == "private"

        return False

    def is_group(self) -> bool:
        if self.chat:
            return self.chat.type in ("supergroup", "group")

        return False

    def is_update_mode(self):
        if self.user_obj and self.user_obj.is_superuser:
            return False

        status = BotStatusService.get_status()
        if status.is_update:
            self.bot.send_message(self.chat_id, text=status.update_msg)
            return True

        return False

    def is_user_block(self):
        if self.user_obj and not self.user_obj.is_active:
            default_msg = "شما در ربات بلاک شده اید"
            msg = MessageService.get_msg_by_step("block")
            self.bot.send_message(self.chat_id, text=msg.text if msg else default_msg)
            return True

        return False

    def has_joined_channel(self, chat_id, user_id):
        chat_id = str(chat_id)
        if chat_id.lstrip("-").isdigit():
            chat_id = int(chat_id)
        else:
            chat_id = chat_id if "@" in chat_id else "@" + chat_id

        rsp = self.bot.get_chat_member(chat_id, user_id)
        return rsp.status != "left"

    def _execute(self, route: Route) -> Any:
        if not route.is_method:
            return route.func(self)

        if isinstance(self, route.owner):
            inst = self

        else:
            inst = route.owner(self.update, self.bot)
            # reuse the already-fetched DB user instead of querying again
            if "user_obj" in self.__dict__:
                inst.__dict__["user_obj"] = self.__dict__["user_obj"]

        return getattr(inst, route.name)()

    def handle(self) -> bool:
        if self.is_update_mode() or self.is_user_block():
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


class MessageHandler(BaseHandler):
    handler_type = "message"
    key_attribute = "text"
    uses_step = True


class CallBackQueryHandler(BaseHandler):
    handler_type = "callback"
    key_attribute = "callback_data"
    uses_step = True


class InlineQueryHandler(BaseHandler):
    handler_type = "inline"
    key_attribute = "query"


class ChosenInlineResultHandler(BaseHandler):
    handler_type = "chosen"
    key_attribute = "result_id"

    @property
    def chosen(self):
        return self.update.chosen_inline_result

    @property
    def result_id(self) -> str:
        return self.chosen.result_id if self.chosen else ""

    @property
    def query(self) -> str:
        return self.chosen.query if self.chosen else ""

    @property
    def user(self):
        return self.chosen.from_user if self.chosen else super().user

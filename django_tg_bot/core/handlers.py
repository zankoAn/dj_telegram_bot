import logging
from typing import Callable, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import make_password
from django.utils.functional import cached_property

from django_tg_bot.contrib.services import BotStatusService, MessageService
from django_tg_bot.core.telegram import Telegram
from django_tg_bot.core.types import (
    CallbackQuery,
    Chat,
    InlineQuery,
    Message,
    Update,
    User,
)

logger = logging.getLogger(__name__)

UserDB = get_user_model()


class BaseHandler:
    """
    Base handler class that provides common utilities for processing Telegram updates,
    such as accessing user, chat, and message details.
    """

    _handlers: dict[str, Callable] = {}
    ALL_KEY = "__all__"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._handlers = {}

    def __init__(self, update: Update, bot: Telegram):
        """
        Initializes the handler with the incoming update and bot instance.
        """
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
        return self.callback_query.data or ""

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
        chat = None
        if self.message:
            chat = self.message.chat

        if self.callback_query and self.callback_query.message:
            chat = self.callback_query.message.chat

        return cast(Chat, chat)

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
        if not self.is_private() or not self.user:
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

    @classmethod
    def add_handler(cls, func: Callable, key):
        if key:
            key = key.replace(" ", "_")
        else:
            key = cls.ALL_KEY

        if key in cls._handlers:
            logger.warning(f"Handler for '{key}' is being overridden!")

        cls._handlers[key] = func

    @classmethod
    def register(cls, key: str | None = None):
        def decorator(func):
            cls.add_handler(func, key)
            return func

        return decorator

    def is_private(self) -> bool:
        if self.chat:
            return self.chat.type == "private"

        if self.inline_query and self.inline_query.from_user:
            return self.inline_query.chat_type in ["private", "sender"]

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

    def handle(self):
        if self.is_update_mode() or self.is_user_block():
            return True

    def dispatch(self, *keys: str):
        for key in (*keys, self.user_step, self.ALL_KEY):
            key = key.replace(" ", "_")
            handler = self._handlers.get(key)
            if handler:
                return handler(self)


class CallBackQueryHandler(BaseHandler):
    def handle(self):
        if super().handle():
            return

        return self.dispatch(self.callback_data)


class InlineQueryHandler(BaseHandler):
    def handle(self):
        if super().handle():
            return True

        return self.dispatch()


class CommandHandler(BaseHandler):
    def handle(self):
        if super().handle():
            return

        return self.dispatch(self.command)


class MessageHandler(BaseHandler):
    def handle(self):
        if super().handle():
            return

        return self.dispatch(self.text)

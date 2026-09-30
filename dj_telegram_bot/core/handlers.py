import logging
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import make_password
from django.utils.functional import cached_property

from dj_telegram_bot.contrib.services import BotStatusService, MessageService
from dj_telegram_bot.core.telegram import Telegram
from dj_telegram_bot.core.types import (
    CallbackQuery,
    Chat,
    InlineQuery,
    Message,
    Update,
    User,
)

logger = logging.getLogger(__name__)

UserDB = get_user_model()


class HandlerRegistry:
    _registry: dict[str, list[tuple[type, str, str]]] = {
        "command": [],
        "message": [],
        "callback": [],
        "inline": [],
    }

    @classmethod
    def register(
        cls, handler_type: str, handler_class: type, pattern: str, method_name: str
    ):
        for existing_class, existing_pattern, _ in cls._registry[handler_type]:
            if existing_pattern == pattern and existing_class == handler_class:
                logger.warning(
                    f"Handler '{pattern}' already registered in {handler_class.__name__}"
                )
                return

        cls._registry[handler_type].append((handler_class, pattern, method_name))
        logger.debug(
            f"Registered: {handler_type} '{pattern}' -> {handler_class.__name__}.{method_name}"
        )

    @classmethod
    def find_handler(cls, handler_type: str, key: str, user_step: str):
        for handler_class, pattern, method_name in cls._registry.get(handler_type, []):
            # step match
            if pattern == user_step:
                return handler_class, method_name

            # exact match
            if pattern == key:
                return handler_class, method_name

            # pattern match
            if cls._matches(pattern, key):
                return handler_class, method_name

        return None

    @staticmethod
    def _matches(pattern: str, key: str) -> bool:
        if "*" not in pattern:
            return False

        if pattern.endswith("*") and not pattern.startswith("*"):
            prefix = pattern[:-1]
            return key == prefix or key.startswith(prefix)

        elif pattern.startswith("*") and not pattern.endswith("*"):
            return key.endswith(pattern[1:])

        elif pattern.startswith("*") and pattern.endswith("*"):
            return pattern[1:-1] in key


class BaseHandler:
    """
    Base handler class that provides common utilities for processing Telegram updates,
    such as accessing user, chat, and message details.
    """

    handler_type: str = None
    key_attribute: str = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for name, method in cls.__dict__.items():
            if hasattr(method, "_handler_pattern"):
                pattern = method._handler_pattern
                handler_type = getattr(method, "_handler_type", "generic")
                HandlerRegistry.register(handler_type, cls, pattern, name)

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

        if self.key_attribute:
            key = getattr(self, self.key_attribute, None)
            if key:
                return self._execute_handler(self.handler_type, key, self.user_step)

    def _execute_handler(self, handler_type: str, key: str, user_step: str):
        result = HandlerRegistry.find_handler(handler_type, key, user_step)
        if result:
            handler_class, method_name = result
            instance = handler_class(self.update, self.bot)
            method = getattr(instance, method_name)
            return method()
        return None


class CommandHandler(BaseHandler):
    handler_type = "command"
    key_attribute = "command"


class MessageHandler(BaseHandler):
    handler_type = "message"
    key_attribute = "text"


class CallBackQueryHandler(BaseHandler):
    handler_type = "callback"
    key_attribute = "callback_data"


class InlineQueryHandler(BaseHandler):
    handler_type = "inline"
    key_attribute = "query"


def command_handler(pattern: str):
    """✅ Command handler decorator"""

    def decorator(func):
        func._handler_pattern = pattern
        func._handler_type = "command"
        return func

    return decorator


def message_handler(pattern: str):
    """✅ Message handler decorator"""

    def decorator(func):
        func._handler_pattern = pattern
        func._handler_type = "message"
        return func

    return decorator


def callback_handler(pattern: str):
    """✅ Callback handler decorator"""

    def decorator(func):
        func._handler_pattern = pattern
        func._handler_type = "callback"
        return func

    return decorator


def inline_handler(pattern: str):
    """✅ Inline handler decorator"""

    def decorator(func):
        func._handler_pattern = pattern
        func._handler_type = "inline"
        return func

    return decorator

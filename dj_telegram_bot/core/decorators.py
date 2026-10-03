from functools import wraps

from django.core.cache import cache

from dj_telegram_bot.contrib.services import ChannelSponsorService, MessageService
from dj_telegram_bot.core.handlers import BaseHandler
from dj_telegram_bot.core.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)


class SponsorGuard:
    SPONSOR_CACHE_KEY = "sponsor_joined:{}:{}"
    SPONSOR_CACHE_TTL = 60  # 1m
    DEFAULT_CALLBACK_DATA = "sponsor_required"

    # keys (step in the database)
    SUBMIT_TEXT_KEY = "sponsor-submit-text"
    PROMPT_TEXT_KEY = "sponsor-prompt-text"
    ERROR_TEXT_KEY = "sponsor-join-error"

    # fallback texts
    DEFAULT_SUBMIT_TEXT = "Confirm membership ✅"
    DEFAULT_PROMPT_TEXT = "To use the bot, please join the channels below."
    DEFAULT_ERROR_TEXT = "Please join the sponsor channels first, then try again."

    def __init__(self, handler: "BaseHandler"):
        self.h = handler

    @staticmethod
    def _db_text(key: str, default: str) -> str:
        msg = MessageService.get_msg_by_step(key)
        return msg.text if msg and msg.text else default

    def get_not_joined(self, use_cache: bool = True) -> list:
        not_joined = []
        for channel in ChannelSponsorService.get_active_channels():
            cache_key = self.SPONSOR_CACHE_KEY.format(self.h.user_id, channel.chat_id)

            if use_cache and cache.get(cache_key):
                continue

            if self.h.has_joined_channel(channel.chat_id, self.h.user_id):
                cache.set(cache_key, True, self.SPONSOR_CACHE_TTL)
            else:
                cache.delete(cache_key)
                not_joined.append(channel)

        return not_joined

    def build_markup(self, channels) -> InlineKeyboardMarkup:
        rows = [[InlineKeyboardButton(text=ch.name, url=ch.link)] for ch in channels]
        submit_text = self._db_text(self.SUBMIT_TEXT_KEY, self.DEFAULT_SUBMIT_TEXT)
        rows.append(
            [
                InlineKeyboardButton(
                    text=submit_text,
                    callback_data=self.DEFAULT_CALLBACK_DATA,
                    style="success",
                )
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def enforce(self, use_cache: bool = True) -> bool:
        not_joined = self.get_not_joined(use_cache)
        if not_joined:
            self.send_prompt(not_joined)
            return False

        return True

    def send_prompt(self, channels) -> None:
        h = self.h
        if h.inline_query:
            return self.on_inline(channels)

        if h.callback_query and not h.chat_id:
            return self.on_inline_message_callback(channels)

        text = self._db_text(self.PROMPT_TEXT_KEY, self.DEFAULT_PROMPT_TEXT)
        h.bot.send_message(
            chat_id=h.chat_id,
            text=text,
            reply_markup=self.build_markup(channels),
        )

    def on_inline_message_callback(self, channels) -> None:
        hook = getattr(self.h, "on_sponsor_callback", None)
        if callable(hook):
            hook(channels)
            return

        text = self._db_text(self.ERROR_TEXT_KEY, self.DEFAULT_ERROR_TEXT)
        self.h.bot.answer_callback_query(
            self.h.callback_query.id,
            text=text,
            show_alert=True,
        )

    def on_inline(self, channels) -> None:
        """Override or set handler.on_sponsor_inline to customize the inline answer."""
        hook = getattr(self.h, "on_sponsor_inline", None)
        if callable(hook):
            hook(channels)
            return

        text = self._db_text(self.ERROR_TEXT_KEY, self.DEFAULT_ERROR_TEXT)
        article = InlineQueryResultArticle(
            id="sponsor-not-joined",
            title=text,
            input_message_content=InputTextMessageContent(message_text=text),
        )
        self.h.bot.answer_inline_query(
            self.h.inline_query.id, [article], cache_time=0, is_personal=True
        )


def sponsor_required(func):
    @wraps(func)
    def wrapper(self: "BaseHandler", *args, **kwargs):
        if not SponsorGuard(self).enforce():
            return False

        return func(self, *args, **kwargs)

    return wrapper

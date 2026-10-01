from functools import wraps

from django.core.cache import cache

from dj_telegram_bot.contrib.services import ChannelSponsorService, MessageService
from dj_telegram_bot.core.handlers import BaseHandler
from dj_telegram_bot.core.types import InlineKeyboardButton, InlineKeyboardMarkup


class SponsorGuard:
    SPONSOR_CACHE_KEY = "sponsor_joined:{}:{}"
    SPONSOR_CACHE_TTL = 60  # 1m
    DEFAULT_SUBMIT_TEXT = "تایید عضویت ✅"
    DEFAULT_CALLBACK_DATA = "sponsor_required"

    def __init__(self, handler: "BaseHandler"):
        self.handler = handler

    def get_not_joined(self, use_cache: bool = True) -> list:
        not_joined = []
        for channel in ChannelSponsorService.get_active_channels():
            cache_key = self.SPONSOR_CACHE_KEY.format(
                self.handler.user_id, channel.chat_id
            )

            if use_cache and cache.get(cache_key):
                continue

            if self.handler.has_joined_channel(channel.chat_id, self.handler.user_id):
                cache.set(cache_key, True, self.SPONSOR_CACHE_TTL)
            else:
                cache.delete(cache_key)
                not_joined.append(channel)

        return not_joined

    def build_markup(self, channels) -> InlineKeyboardMarkup:
        rows = [[InlineKeyboardButton(text=ch.name, url=ch.link)] for ch in channels]
        rows.append(
            [
                InlineKeyboardButton(
                    text=self.DEFAULT_SUBMIT_TEXT,
                    callback_data=self.DEFAULT_CALLBACK_DATA,
                    style="success",
                )
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def send_prompt(self, channels) -> None:
        msg = MessageService.get_msg_by_step(self.DEFAULT_CALLBACK_DATA)
        self.handler.bot.send_message(
            chat_id=self.handler.chat_id,
            text=msg.text if msg else ChannelSponsorService.default_msg,
            reply_markup=self.build_markup(channels),
        )

    def enforce(self, use_cache: bool = True) -> bool:
        not_joined = self.get_not_joined(use_cache)
        if not_joined:
            self.send_prompt(not_joined)
            return False

        return True


def sponsor_required(func):
    @wraps(func)
    def wrapper(self: "BaseHandler", *args, **kwargs):
        if not SponsorGuard(self).enforce():
            return False

        return func(self, *args, **kwargs)

    return wrapper

from functools import wraps

from django.core.cache import cache

from apps.telegram.handlers import BaseHandler
from apps.telegram.services import ChannelSponsorService, MessageService
from apps.telegram.telegram_models import InlineKeyboardButton, InlineKeyboardMarkup

SPONSOR_CACHE_KEY = "sponsor_joined:{}:{}"
SPONSOR_CACHE_TTL = 60  # 1m
DEFAULT_SUBMIT_TEXT = "تایید عضویت ✅"


def sponsor_required(func):
    @wraps(func)
    def wrapper(self: BaseHandler, *args, **kwargs):
        sponsor_channels = ChannelSponsorService.get_active_channels()
        if not sponsor_channels:
            return True

        not_joined = []
        for channel in sponsor_channels:
            cache_key = SPONSOR_CACHE_KEY.format(self.user_id, channel.chat_id)
            if cache.get(cache_key):
                continue

            if self.has_joined_channel(channel.chat_id, self.user_id):
                cache.set(cache_key, True, SPONSOR_CACHE_TTL)
                continue

            not_joined.append(channel)

        if not_joined:
            msg = MessageService.get_msg_by_step("sponsor_required")
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=ch.name, url=ch.link)]
                    for ch in not_joined
                ]
            )
            markup.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=DEFAULT_SUBMIT_TEXT,
                        callback_data="sponsor_required",
                        style="success",
                    )
                ]
            )
            self.bot.send_message(
                chat_id=self.chat_id,
                text=msg.text if msg else ChannelSponsorService.default_msg,
                reply_markup=markup,
            )
            return False

        return func(self, *args, **kwargs)

    return wrapper

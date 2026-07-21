from functools import lru_cache

from django.conf import settings
from django.core.cache import cache

from django_tg_bot.contrib.models import BotUpdateStatus, ChannelSponsor, Message


@lru_cache
def get_tm_client():
    from django_tg_bot.core.telegram import Telegram

    return Telegram(
        token=settings.BOT_TOKEN,
        webhook_url=settings.TM_WEBHOOK_URL,
        proxy_socks=getattr(settings, "PROXY_SOCKS", None),
    )


class BotStatusService:
    CACHE_KEY = "bot_update_status"
    CACHE_TTL = 60

    @staticmethod
    def get_status() -> BotUpdateStatus:
        status = cache.get(BotStatusService.CACHE_KEY)
        if status is None:
            status, _ = BotUpdateStatus.objects.get_or_create(id=1)
            cache.set(BotStatusService.CACHE_KEY, status, BotStatusService.CACHE_TTL)

        return status

    @staticmethod
    def is_updating() -> bool:
        return BotStatusService.get_status().is_update

    @staticmethod
    def set_updating(is_updating: bool) -> None:
        BotUpdateStatus.objects.update_or_create(
            id=1, defaults={"is_update": is_updating}
        )
        cache.delete(BotStatusService.CACHE_KEY)


class ChannelSponsorService:
    default_msg = "برای استفاده از ربات لطفا در کانالهای زیر عضو شوید"

    @staticmethod
    def get_active_channels():
        return ChannelSponsor.objects.filter(is_active=True)

    @staticmethod
    def get_channel_by_chat_id(chat_id: str):
        return ChannelSponsor.objects.filter(chat_id=chat_id).first()


class MessageService:
    @staticmethod
    def get_msg_by_step(step: str) -> Message | None:
        return (
            Message.objects.select_related("keyboard")
            .prefetch_related("keyboard__key_buttons")
            .filter(related_step=step)
            .first()
        )

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.bot.mixins import TelegramUserMixin


class User(AbstractUser, TelegramUserMixin):
    is_send_ads = models.BooleanField(
        default=False, verbose_name=_("Advertising status")
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["user_id"]

    def __str__(self):
        return str(self.user_id)

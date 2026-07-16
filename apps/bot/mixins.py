from django.db import models
from django.utils.translation import gettext_lazy as _


class TelegramUserMixin(models.Model):
    user_id = models.BigIntegerField(unique=True, verbose_name=_("user id"))
    step = models.CharField(
        max_length=30, default="home", verbose_name=_("current step")
    )

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.user_id)

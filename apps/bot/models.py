import json

from django.db import models


class BotUpdateStatus(models.Model):
    is_update = models.BooleanField(default=False)
    update_msg = models.TextField(default="bot is updated !")

    def save(self, *args, **kwargs):
        self.id = 1
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(f"Bot status is: {self.is_update}")


class ChannelSponsor(models.Model):
    name = models.CharField(max_length=70, null=True, blank=True)
    chat_id = models.CharField(max_length=70, unique=True, null=True, blank=True)
    link = models.CharField(max_length=70, unique=True)
    is_active = models.BooleanField(default=False)

    PREFIX = "-100"

    def save(self, *args, **kwargs):
        if self.chat_id and not f"{self.chat_id}".startswith(self.PREFIX):
            self.chat_id = f"{self.PREFIX}{self.chat_id}"

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)


class Message(models.Model):
    text = models.TextField(null=True, blank=True)
    related_step = models.CharField(
        max_length=80,
        default="home",
        verbose_name="related step",
    )

    def __str__(self) -> str:
        return f"{self.related_step}"


class Keyboard(models.Model):
    KEYBOARD_TYPE_CHOICES = [
        ("REPLY", "Reply Keyboard Markup"),
        ("INLINE", "Inline Keyboard Markup"),
    ]

    message = models.OneToOneField(
        Message, on_delete=models.CASCADE, related_name="keyboard"
    )
    keyboard_type = models.CharField(
        max_length=10, choices=KEYBOARD_TYPE_CHOICES, default="REPLY"
    )
    resize_keyboard = models.BooleanField(default=True)
    one_time_keyboard = models.BooleanField(default=False)

    def __str__(self):
        return f"Keyboard for Message {self.message.id} ({self.keyboard_type})"


class Button(models.Model):
    keyboard = models.ForeignKey(
        Keyboard, on_delete=models.CASCADE, related_name="key_buttons"
    )
    text = models.CharField(max_length=255)
    row = models.PositiveIntegerField(default=0)
    column = models.PositiveIntegerField(default=0)
    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Button: {self.text} (Row {self.row}, Pos {self.column})"

    def data_as_json(self):
        return json.dumps(self.data)

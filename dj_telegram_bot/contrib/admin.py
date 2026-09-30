import json

from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.utils.translation import gettext as _

from dj_telegram_bot.contrib.models import (
    BotUpdateStatus,
    Button,
    ChannelSponsor,
    Keyboard,
    Message,
)


@admin.register(BotUpdateStatus)
class BotUpdateStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "is_update", "text")
    list_editable = ("is_update",)

    def text(self, obj):
        return obj.update_msg[:30]


@admin.register(ChannelSponsor)
class ChannelSponsorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "chat_id", "is_active")
    search_fields = ("name",)
    list_editable = ("is_active",)
    list_display_links = ("id", "name")

    def _link(self, obj):
        return obj.link[:30]


class MessageAdminForm(forms.ModelForm):
    keyboard_data = forms.JSONField(required=False)

    class Meta:
        model = Message
        fields = "__all__"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    form = MessageAdminForm
    change_form_template = "admin/bot/messages/keyboard_builder_change_form.html"

    BUTTON_DATA_FIELDS = (
        "url",
        "callback_data",
        "copy_text",
        "style",
        "request_contact",
        "request_location",
        "web_app",
        "login_url",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        keyboard_json = request.POST.get("keyboard_data")
        if not keyboard_json:
            return

        try:
            data = json.loads(keyboard_json)
        except json.JSONDecodeError:
            self.message_user(
                request,
                _("داده‌ی کیبورد نامعتبر است (JSON خراب)."),
                level=messages.ERROR,
            )
            return

        try:
            with transaction.atomic():
                if hasattr(obj, "keyboard") and obj.keyboard:
                    obj.keyboard.delete()

                keyboard = Keyboard.objects.create(
                    message=obj,
                    keyboard_type=data.get("keyboard_type", "REPLY"),
                    one_time_keyboard=data.get("one_time_keyboard", False),
                    resize_keyboard=data.get("resize_keyboard", True),
                )
                buttons = [
                    Button(
                        keyboard=keyboard,
                        text=btn_data.get("text", ""),
                        row=btn_data.get("row", 1),
                        column=btn_data.get("column", 1),
                        data=self._extract_button_data(btn_data),
                    )
                    for btn_data in data.get("buttons", [])
                ]
                if buttons:
                    Button.objects.bulk_create(buttons)

                self.message_user(
                    request,
                    _("کیبورد و دکمه‌ها با موفقیت ذخیره شدند."),
                    level=messages.SUCCESS,
                )

        except Exception as e:
            self.message_user(
                request, _(f"خطا در ذخیره کیبورد: {str(e)}"), level=messages.ERROR
            )

    def _extract_button_data(self, btn_data):
        raw = btn_data.get("data") or {}
        return {field: raw.get(field) for field in self.BUTTON_DATA_FIELDS}

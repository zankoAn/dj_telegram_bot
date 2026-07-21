from django_tg_bot.core.types import (
    CopyTextButton,
    InlineButtonOverride,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LoginUrl,
    ReplyButtonOverride,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


class ReplyKeyboardBuilder:
    def build(
        self,
        keyboard,
        buttons,
        override_reply: ReplyButtonOverride | None = None,
    ) -> ReplyKeyboardMarkup:
        markup = []
        current_row = []
        last_row = None

        for button in buttons:
            if last_row is not None and button.row != last_row:
                markup.append(current_row)
                current_row = []
            if (
                override_reply
                and button.row == override_reply.row
                and button.column == override_reply.column
            ):
                override = override_reply
            else:
                override = ReplyButtonOverride()

            web_app = button.data.get("web_app")
            current_row.append(
                KeyboardButton(
                    text=button.text,
                    style=button.data.get("style"),
                    request_contact=button.data.get("request_contact"),
                    request_location=button.data.get("request_location"),
                    web_app=WebAppInfo(url=web_app) if web_app else None,
                    request_poll=override.request_poll,
                    request_users=override.request_users,
                    request_chat=override.request_chat,
                    request_managed_bot=override.request_managed_bot,
                    icon_custom_emoji_id=override.icon_custom_emoji_id,
                )
            )
            last_row = button.row

        if current_row:
            markup.append(current_row)

        return ReplyKeyboardMarkup(
            keyboard=markup,
            resize_keyboard=keyboard.resize_keyboard,
            one_time_keyboard=keyboard.one_time_keyboard,
        )


class InlineKeyboardBuilder:
    def build(
        self,
        buttons,
        override_inline: InlineButtonOverride | None = None,
    ) -> InlineKeyboardMarkup:
        markup = []
        current_row = []
        last_row = None

        for button in buttons:
            if last_row is not None and button.row != last_row:
                markup.append(current_row)
                current_row = []

            if (
                override_inline
                and button.row == override_inline.row
                and button.column == override_inline.column
            ):
                override = override_inline
            else:
                override = InlineButtonOverride()

            web_app = button.data.get("web_app")
            copy_text = button.data.get("copy_text")
            login_url = button.data.get("login_url")
            current_row.append(
                InlineKeyboardButton(
                    text=button.text,
                    callback_data=button.data.get("callback_data"),
                    url=button.data.get("url"),
                    style=button.data.get("style"),
                    web_app=WebAppInfo(url=web_app) if web_app else None,
                    copy_text=CopyTextButton(text=copy_text) if copy_text else None,
                    login_url=LoginUrl(url=login_url) if login_url else None,
                    switch_inline_query=override.switch_inline_query,
                    switch_inline_query_current_chat=override.switch_inline_query_current_chat,
                    switch_inline_query_chosen_chat=override.switch_inline_query_chosen_chat,
                    callback_game=override.callback_game,
                    icon_custom_emoji_id=override.icon_custom_emoji_id,
                    pay=override.pay,
                )
            )
            last_row = button.row

        if current_row:
            markup.append(current_row)

        return InlineKeyboardMarkup(inline_keyboard=markup)


class KeyboardBuilder:
    def __init__(self, msg_obj=None, keyboard_obj=None, btn_obj=None) -> None:
        self.message = msg_obj
        self.keyboard = keyboard_obj
        self.button = btn_obj

    def _collect_buttons_for_context(self):
        """
        Collects all keyboards associated with the given message/keyboard.
        """
        if not any([self.message, self.keyboard, self.button]):
            raise ValueError("No keyboard available to build reply markup")

        if self.button:
            keyboard = self.button.keyboard

        if self.message:
            keyboard = self.message.keyboard

        if self.keyboard:
            keyboard = self.keyboard

        btns = keyboard.key_buttons.all().order_by("row", "column")
        return keyboard, btns

    def build(
        self,
        override_inline: InlineButtonOverride | None = None,
        override_reply: ReplyButtonOverride | None = None,
    ) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
        keyboard, buttons = self._collect_buttons_for_context()
        if keyboard.keyboard_type == "INLINE":
            keyboard = InlineKeyboardBuilder().build(
                buttons=buttons, override_inline=override_inline
            )
        else:
            keyboard = ReplyKeyboardBuilder().build(
                keyboard=keyboard, buttons=buttons, override_reply=override_reply
            )

        return keyboard

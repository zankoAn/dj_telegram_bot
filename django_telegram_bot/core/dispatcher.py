from django_telegram_bot.core.handlers import (
    CallBackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
)
from django_telegram_bot.core.telegram import Telegram
from django_telegram_bot.core.types import Update


class Dispatcher:
    """
    Dispatcher is responsible for routing incoming Telegram updates to the appropriate handler
    based on the type of content in the update.

    Attributes:
        update(Update): The incoming update object from Telegram.

    Methods:
        dispatch():
            Routes the update to the appropriate handler:

            1. CommandHandler: If the message starts with '/'.
            2. CallBackQueryHandler: If the update contains a callback_query.
            3. InlineQueryHandler: If the update contains an inline_query.
            4. MessageHandler: Default handler for text messages or unhandled types.

    Returns:
        The result of the specific handler's handle() method.
    """

    def __init__(self, update: Update, bot: Telegram):
        self.update = update
        self.bot = bot

    def dispatch(self):
        if self.update.inline_query:
            return InlineQueryHandler(update=self.update, bot=self.bot).handle()

        if self.update.callback_query:
            return CallBackQueryHandler(update=self.update, bot=self.bot).handle()

        if self.update.message:
            if self.update.message.text and self.update.message.text.startswith("/"):
                return CommandHandler(update=self.update, bot=self.bot).handle()

        return MessageHandler(update=self.update, bot=self.bot).handle()

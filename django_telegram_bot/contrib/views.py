import logging
import traceback

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django_telegram_bot.contrib.services import get_tm_client
from django_telegram_bot.core.dispatcher import Dispatcher
from django_telegram_bot.core.types import Update

logger = logging.getLogger(__name__)


class TelegramWebhookView(APIView):
    """
    A Django REST Framework API view that handles incoming POST requests from the Telegram Bot API.

    This view:
    - Parses the incoming JSON payload from Telegram.
    - Constructs an `Update` object from the payload.
    - Passes the update to the `Dispatcher` to determine how it should be handled.
    - Logs any exceptions that occur during processing.

    Returns:
        JSON response indicating success ({"ok": True}).
    """

    def post(self, request: Request) -> Response:
        """
        Handles incoming Telegram webhook POST request.

        Args:
            request (Request): The incoming HTTP request from Telegram containing the update payload.

        Returns:
            Response: A JSON response with a success message.
        """
        try:
            update = Update.model_validate(request.data)
            bot = get_tm_client()
            logger.info(
                f"Received Telegram update: {update.model_dump(exclude_none=True)}"
            )
            Dispatcher(update, bot).dispatch()

        except Exception:
            error_msg = traceback.format_exc().strip()
            logger.error(f"Exception while processing Telegram update:\n{error_msg}")

        return Response({"ok": True}, status=status.HTTP_200_OK)

import json
import logging
import traceback

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from dj_telegram_bot.contrib.services import get_tm_client
from dj_telegram_bot.core.dispatcher import Dispatcher
from dj_telegram_bot.core.types import Update

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    """
    A Django API view that handles incoming POST requests from the Telegram Bot API.

    This view:
    - Parses the incoming JSON payload from Telegram.
    - Constructs an `Update` object from the payload.
    - Passes the update to the `Dispatcher` to determine how it should be handled.
    - Logs any exceptions that occur during processing.

    Returns:
        JSON response indicating success ({"ok": True}).
    """

    def post(self, request, *args, **kwargs) -> JsonResponse:
        """
        Handles incoming Telegram webhook POST request.

        Args:
            request: The incoming HTTP request from Telegram containing the update payload.

        Returns:
            JsonResponse: A JSON response with a success message.
        """
        try:
            data = json.loads(request.body.decode("utf-8"))
            update = Update.model_validate(data)

            bot = get_tm_client()
            logger.info(
                f"Received Telegram update: {update.model_dump(exclude_none=True)}"
            )

            Dispatcher(update, bot).dispatch()

        except Exception:
            error_msg = traceback.format_exc().strip()
            logger.error(f"Exception while processing Telegram update:\n{error_msg}")

        return JsonResponse({"ok": True}, status=200)

from django.urls import path

from django_telegram_bot.contrib.views import TelegramWebhookView

app_name = "bot"
urlpatterns = [
    path("webhook/", TelegramWebhookView.as_view(), name="webhook"),
]

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ContribConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dj_telegram_bot.contrib"

    def ready(self):
        self._validate_user_model()
        self._autodiscover_handlers()

    @staticmethod
    def _autodiscover_handlers():
        import importlib
        from pathlib import Path

        from django.apps import apps

        HANDLERS_DIR_NAME = "bot_handlers"

        for app_config in apps.get_app_configs():
            handlers_dir = Path(app_config.path) / HANDLERS_DIR_NAME

            if not handlers_dir.is_dir():
                continue

            for py_file in handlers_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"{app_config.name}.{HANDLERS_DIR_NAME}.{py_file.stem}"

                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    logger.error(
                        f"Warning: Could not import handler {module_name}: {e}"
                    )

    @staticmethod
    def _validate_user_model():
        from django.contrib.auth import get_user_model
        from django.core.exceptions import ImproperlyConfigured

        from dj_telegram_bot.contrib.mixins import TelegramUserMixin

        User = get_user_model()

        if not issubclass(User, TelegramUserMixin):
            raise ImproperlyConfigured(
                "dj_telegram_bot requires your custom AUTH_USER_MODEL to inherit "
                "from `TelegramUserMixin`.\n\n"
                "Example:\n"
                "    from django.contrib.auth.models import AbstractUser\n"
                "    from dj_telegram_bot.contrib.mixins import TelegramUserMixin\n\n"
                "    class User(AbstractUser, TelegramUserMixin):\n"
                "        pass\n\n"
                "Then in settings.py:\n"
                "    AUTH_USER_MODEL = 'your_app.User'"
            )

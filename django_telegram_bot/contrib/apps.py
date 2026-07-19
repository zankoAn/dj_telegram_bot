import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ContribConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_telegram_bot.contrib"

    def ready(self):
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

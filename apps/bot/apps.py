from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bot"

    def ready(self):
        self._autodiscover_handlers()

    @staticmethod
    def _autodiscover_handlers():
        import importlib
        from pathlib import Path

        from django.apps import apps

        for app_config in apps.get_app_configs():
            handlers_dir = Path(app_config.path) / "handlers"

            if not handlers_dir.is_dir():
                continue

            for py_file in handlers_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"{app_config.name}.handlers.{py_file.stem}"

                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    print(f"Warning: Could not import handler {module_name}: {e}")

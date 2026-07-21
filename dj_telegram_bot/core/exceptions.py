class TelegramError(Exception):
    """Base exception for all Telegram API related errors."""

    pass


class TelegramAPIError(TelegramError):
    """Raised when Telegram API returns ok: false."""

    def __init__(self, method: str, error_code: int | None, description: str):
        self.method = method
        self.error_code = error_code
        self.description = description
        super().__init__(f"[{method}] ({error_code}): {description}")

    def __repr__(self) -> str:
        return (
            f"TelegramAPIError(method={self.method!r}, "
            f"error_code={self.error_code!r}, description={self.description!r})"
        )

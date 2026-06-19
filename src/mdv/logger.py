import logging
from typing import Optional

_LOGGER_NAME = "mdv"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    full_name = f"{_LOGGER_NAME}.{name}" if name else _LOGGER_NAME
    logger = logging.getLogger(full_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s] %(module)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


class IgnoreStaticFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return "/static/" not in message and "favicon.ico" not in message


# Suppress verbose static asset and favicon logs from Werkzeug
logging.getLogger("werkzeug").addFilter(IgnoreStaticFilter())

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


# Quiet Werkzeug request logging by default
logging.getLogger("werkzeug").setLevel(logging.WARNING)


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    # Set level for the main package logger
    logging.getLogger(_LOGGER_NAME).setLevel(level)
    # Set level for all dynamically registered child loggers
    for name in logging.root.manager.loggerDict:
        if name.startswith(_LOGGER_NAME):
            logging.getLogger(name).setLevel(level)

    # Set level for the werkzeug logger
    logging.getLogger("werkzeug").setLevel(logging.INFO if debug else logging.WARNING)

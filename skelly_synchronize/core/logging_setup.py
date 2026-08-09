import logging

_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure process-wide logging.

    This is opt-in and must only be called once, from an application entry
    point (the CLI or API `main.py`) -- never from inside `core` itself.
    Library modules within `core` use `logging.getLogger(__name__)` only.
    """
    logging.basicConfig(level=level, format=_DEFAULT_FORMAT)

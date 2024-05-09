import logging

from rich.logging import RichHandler

_IS_VERBOSE = True
LOG = logging.getLogger("labelle")
VERBOSE_NOTICE = "Run with --verbose for more information"


def _update_log_level() -> None:
    LOG.setLevel(logging.DEBUG if _IS_VERBOSE else logging.INFO)


def set_not_verbose() -> None:
    global _IS_VERBOSE
    _IS_VERBOSE = False
    _update_log_level()


def is_verbose() -> bool:
    return _IS_VERBOSE


def configure_logging() -> None:
    _update_log_level()
    LOG.addHandler(RichHandler())


def print_exception(e: Exception) -> None:
    if _IS_VERBOSE:
        LOG.exception(e)
    else:
        LOG.error(f"{e!r}")
        LOG.error(VERBOSE_NOTICE)

import logging
import sys

_IS_VERBOSE = True
LOG = logging.getLogger("labelle")
VERBOSE_NOTICE = "Run with --verbose for more information"


def _update_log_level():
    LOG.setLevel(logging.DEBUG if _IS_VERBOSE else logging.INFO)


def set_not_verbose() -> None:
    global _IS_VERBOSE
    _IS_VERBOSE = False
    _update_log_level()


def is_verbose() -> bool:
    return _IS_VERBOSE


def configure_logging():
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    _update_log_level()
    LOG.addHandler(handler)


def print_exception(e: Exception) -> None:
    if _IS_VERBOSE:
        LOG.exception(e)
    else:
        LOG.error(f"{e!r}")
        LOG.error(VERBOSE_NOTICE)

import logging
import traceback

from PyQt6.QtWidgets import (
    QMessageBox,
)

from dymoprint.lib.logger import VERBOSE_NOTICE, is_verbose, print_exception

LOG = logging.getLogger(__name__)


def crash_msg_box(parent, title, err):
    print_exception(err)
    text = f"{err}\n\n{traceback.format_exc() if is_verbose() else VERBOSE_NOTICE}"
    QMessageBox.warning(parent, title, text)

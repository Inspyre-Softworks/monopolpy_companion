"""PySide6 application bootstrap; import only when Qt GUI is requested."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from monopolpy_companion.controller import SessionController
from .main_window import MainWindow
from .theme import stylesheet


def run() -> int:
    """Launch the responsive desktop dashboard and return Qt's exit code."""
    application = QApplication.instance()
    owns_app = application is None
    if application is None:
        application = QApplication(sys.argv)
    application.setApplicationName('MonopolPy Companion')
    application.setOrganizationName('Inspyre Softworks')
    application.setStyleSheet(stylesheet(True))
    window = MainWindow(SessionController())
    window.show()
    if not owns_app:
        # Embedded Qt hosts already have their own event loop.
        return 0
    return application.exec()

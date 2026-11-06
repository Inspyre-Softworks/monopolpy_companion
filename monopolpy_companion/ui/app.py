"""PySide6 application bootstrap; import only when Qt GUI is requested."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from monopolpy_companion.controller import SessionController
from .main_window import MainWindow
from .branding import make_app_icon
from .theme import stylesheet
from .fonts import body_font, load_user_font


def run(enabled_plugins: list[str] | None = None) -> int:
    """Launch the responsive desktop dashboard and return Qt's exit code."""
    application = QApplication.instance()
    owns_app = application is None
    if application is None:
        application = QApplication(sys.argv)
    load_user_font()
    application.setStyle('Fusion')
    application.setFont(body_font(10))
    application.setApplicationName('MonopolPy Companion')
    application.setWindowIcon(make_app_icon())
    application.setOrganizationName('Inspyre Softworks')
    application.setStyleSheet(stylesheet(True))
    window = MainWindow(SessionController(), enabled_plugins=enabled_plugins)
    window.show()
    if not owns_app:
        # Embedded Qt hosts already have their own event loop.
        return 0
    return application.exec()

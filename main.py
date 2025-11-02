# main.py
from __future__ import annotations
import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon   # <-- already imported, needed for logo

from ui.main_window import MainWindow


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log", encoding="utf-8"),
        ],
    )

    def excepthook(exctype, value, tb):
        logging.exception("Unhandled exception", exc_info=(exctype, value, tb))
        try:
            QMessageBox.critical(None, "Application Error", f"{exctype.__name__}: {value}")
        except Exception:
            pass
        sys.exit(1)

    sys.excepthook = excepthook


def load_stylesheet(app: QApplication) -> None:
    qss = Path("resources/style.qss")
    if qss.exists():
        try:
            app.setStyleSheet(qss.read_text(encoding="utf-8"))
        except Exception as e:
            logging.warning("Failed to load stylesheet: %s", e)


def main() -> int:
    setup_logging()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Typemaster")
    app.setOrganizationName("Typemaster")

    # ✅ Set Application + Window Icon
    app.setWindowIcon(QIcon("assets/logo.png"))

    load_stylesheet(app)

    win = MainWindow()
    win.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

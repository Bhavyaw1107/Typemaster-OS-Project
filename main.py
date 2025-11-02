from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import Qt
import sys
from ui.main_window import MainWindow
from utils.file_handler import ensure_app_files

def load_fonts():
    # Optional bundled fonts
    for path in (
        "assets/fonts/Inter-Regular.ttf",
        "assets/fonts/Inter-Medium.ttf",
        "assets/fonts/Inter-Bold.ttf",
    ):
        try:
            QFontDatabase.addApplicationFont(path)
        except Exception:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)

    ensure_app_files()
    load_fonts()

    win = MainWindow()
    win.show()
    sys.exit(app.exec())

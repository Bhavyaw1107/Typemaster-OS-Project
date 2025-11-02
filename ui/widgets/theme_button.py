from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Qt

class ThemeButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("")
        self.setToolTip("Change theme")
        self.setFixedSize(QSize(36, 36))
        self.setIcon(QIcon("assets/logo.png"))
        self.setIconSize(QSize(24, 24))
        self.setCursor(Qt.PointingHandCursor)

# ui/widgets/session_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox
)

class SessionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Session")
        self.setFixedSize(340, 210)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Time limit
        layout.addWidget(QLabel("Time limit:", self))
        self.cmb_time = QComboBox(self)
        self.cmb_time.addItems(["Unlimited", "15", "30", "60", "120"])
        layout.addWidget(self.cmb_time)

        # Text source
        layout.addWidget(QLabel("Text source:", self))
        self.cmb_source = QComboBox(self)
        self.cmb_source.addItems([
            "Paragraph",
            "Quotes",
            "Code Snippets",
            "Numbers",
            "Punctuation",
        ])
        layout.addWidget(self.cmb_source)

        # Buttons
        row = QHBoxLayout()
        btn_start = QPushButton("Start", self)
        btn_start.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_start)
        row.addWidget(btn_cancel)

        layout.addStretch(1)
        layout.addLayout(row)

    @property
    def config(self):
        return {
            "time_limit": None if self.cmb_time.currentText() == "Unlimited"
                          else int(self.cmb_time.currentText()),
            "source": self.cmb_source.currentText(),
        }

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox, QPushButton, QFileDialog, QMessageBox
from PySide6.QtCore import Qt

class SessionEditor(QDialog):
    """
    Returns config via .result_config after accept():
    { "time_limit": seconds or None, "text_path": str or None, "include_punct": bool, "include_numbers": bool }
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Session")
        self.resize(520, 260)
        self.result_config = None

        root = QVBoxLayout(self)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Time limit:"))
        self.time_combo = QComboBox()
        self.time_combo.addItems(["Unlimited", "15s", "30s", "60s", "Custom…"])
        self.time_combo.currentIndexChanged.connect(self._time_changed)
        row1.addWidget(self.time_combo)
        self.custom_secs = QSpinBox()
        self.custom_secs.setRange(5, 3600)
        self.custom_secs.setValue(120)
        self.custom_secs.setEnabled(False)
        row1.addWidget(QLabel("secs"))
        row1.addWidget(self.custom_secs)
        row1.addStretch(1)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Text source:"))
        self.text_label = QLabel("Current default text")
        self.btn_browse = QPushButton("Load file…")
        self.btn_browse.clicked.connect(self._browse_text)
        row2.addWidget(self.text_label, stretch=1)
        row2.addWidget(self.btn_browse)
        root.addLayout(row2)

        self.chk_punct = QCheckBox("Include punctuation")
        self.chk_punct.setChecked(True)
        self.chk_numbers = QCheckBox("Include numbers")
        self.chk_numbers.setChecked(True)
        root.addWidget(self.chk_punct)
        root.addWidget(self.chk_numbers)

        btns = QHBoxLayout()
        btns.addStretch(1)
        ok = QPushButton("Start"); ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        btns.addWidget(ok); btns.addWidget(cancel)
        root.addLayout(btns)

        self._chosen_text_path = None

    def _time_changed(self):
        self.custom_secs.setEnabled(self.time_combo.currentText() == "Custom…")

    def _browse_text(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open text", "", "Text Files (*.txt)")
        if not path:
            return
        self._chosen_text_path = path
        self.text_label.setText(path)

    def _accept(self):
        t = self.time_combo.currentText()
        if t == "Unlimited":
            time_limit = None
        elif t in ("15s", "30s", "60s"):
            time_limit = int(t[:-1])
        else:
            time_limit = self.custom_secs.value()

        self.result_config = {
            "time_limit": time_limit,
            "text_path": self._chosen_text_path,
            "include_punct": self.chk_punct.isChecked(),
            "include_numbers": self.chk_numbers.isChecked(),
        }
        self.accept()

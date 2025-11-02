from PySide6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QColorDialog, QLineEdit, QFileDialog, QMessageBox
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import json, os
from app.themes import add_runtime_theme_from_dict

_FIELDS = [
    ("bg", "Background"),
    ("surface", "Surface"),
    ("text", "Text"),
    ("text_muted", "Text (muted)"),
    ("correct", "Correct"),
    ("error", "Error"),
    ("caret", "Caret"),
    ("accent", "Accent"),
    ("graph_line", "Graph line"),
]

class ThemeEditor(QDialog):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor")
        self.resize(560, 380)
        self._values = {
            "name": theme.name,
            "bg": theme.bg,
            "surface": theme.surface,
            "text": theme.text,
            "text_muted": theme.text_muted,
            "correct": theme.correct,
            "error": theme.error,
            "caret": theme.caret,
            "accent": theme.accent,
            "graph_line": theme.graph_line,
            "sfx_key": theme.sfx_key,
            "sfx_ok": theme.sfx_ok,
            "sfx_err": theme.sfx_err,
        }

        root = QVBoxLayout(self)
        grid = QGridLayout(); row = 0

        grid.addWidget(QLabel("Theme name:"), row, 0)
        self.name_edit = QLineEdit(self._values["name"])
        grid.addWidget(self.name_edit, row, 1, 1, 2); row += 1

        self.color_btns = {}
        for key, label in _FIELDS:
            grid.addWidget(QLabel(label + ":"), row, 0)
            btn = QPushButton(self._values[key])
            btn.clicked.connect(lambda _=False, k=key: self._pick_color(k))
            self.color_btns[key] = btn
            grid.addWidget(btn, row, 1, 1, 2)
            row += 1

        root.addLayout(grid)

        act = QGridLayout()
        self.btn_save_as = QPushButton("Save As…"); self.btn_save_as.clicked.connect(self._save_as)
        self.btn_load = QPushButton("Load From File…"); self.btn_load.clicked.connect(self._load_from_file)
        self.btn_apply = QPushButton("Apply (session only)"); self.btn_apply.clicked.connect(self._apply_session_only)
        act.addWidget(self.btn_save_as, 0, 0); act.addWidget(self.btn_load, 0, 1); act.addWidget(self.btn_apply, 0, 2)
        root.addLayout(act)

    def _pick_color(self, key):
        c = QColorDialog.getColor(QColor(self._values[key]), self, f"Pick {key}")
        if c.isValid():
            hexv = c.name()
            self._values[key] = hexv
            self.color_btns[key].setText(hexv)

    def _save_as(self):
        os.makedirs("assets/themes", exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Save Theme As", "assets/themes/custom_theme.json", "Theme JSON (*.json)")
        if not path: return
        data = dict(self._values)
        data["name"] = self.name_edit.text().strip() or "Custom Theme"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        add_runtime_theme_from_dict(data)
        QMessageBox.information(self, "Theme", "Saved and added to theme list.")

    def _load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Theme", "assets/themes", "Theme JSON (*.json)")
        if not path: return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in self._values:
            if k in data:
                self._values[k] = data[k]
        self.name_edit.setText(data.get("name", self._values["name"]))
        for k, btn in self.color_btns.items():
            btn.setText(self._values[k])
        add_runtime_theme_from_dict(data)
        QMessageBox.information(self, "Theme", "Loaded and added to theme list.")

    def _apply_session_only(self):
        data = dict(self._values)
        data["name"] = self.name_edit.text().strip() or "Custom Theme"
        add_runtime_theme_from_dict(data)
        QMessageBox.information(self, "Theme", "Applied to session theme list.")
        self.accept()

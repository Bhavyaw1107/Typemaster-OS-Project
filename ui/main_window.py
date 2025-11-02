from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QToolBar, QMenu, QFileDialog, QMessageBox
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt
import json

from ui.test_ui import TestUI
from app.themes import THEMES, DEFAULT_THEME_INDEX, load_custom_themes
from utils.file_handler import load_default_text
from utils.db_helper import upsert_user, insert_result
from ui.weakkeys_dialog import WeakKeysDialog
from ui.session_editor import SessionEditor
from ui.theme_editor import ThemeEditor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Typemaster")
        self.resize(1200, 720)
        self.user_id = upsert_user("guest")

        load_custom_themes()

        self._build_toolbar()

        central = QWidget()
        lay = QHBoxLayout(central)
        self.test = TestUI()
        self.test.set_text(load_default_text())
        self.test.finished.connect(self._on_test_finished)
        lay.addWidget(self.test)
        self.setCentralWidget(central)

        self._apply_theme(DEFAULT_THEME_INDEX)

    def _build_toolbar(self):
        self.tb = QToolBar("Toolbar")
        self.tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.tb)

        self.theme_btn = QAction(QIcon("assets/logo.png"), "Theme", self)
        self.theme_menu = QMenu("Themes", self)
        self.theme_btn.setMenu(self.theme_menu)
        self.tb.addAction(self.theme_btn)
        self._rebuild_theme_menu()

        act_session = QAction("Session…", self); act_session.triggered.connect(self._open_session)
        self.tb.addAction(act_session)

        act_weak = QAction("Weak Keys…", self); act_weak.triggered.connect(self._open_weakkeys)
        self.tb.addAction(act_weak)

        act_theme_editor = QAction("Theme Editor…", self); act_theme_editor.triggered.connect(self._open_theme_editor)
        self.tb.addAction(act_theme_editor)

        load_text = QAction("Load text…", self); load_text.triggered.connect(self._load_text_from_file)
        self.tb.addAction(load_text)

        reset = QAction("Reset test", self); reset.triggered.connect(self._reset_test)
        self.tb.addAction(reset)

    def _rebuild_theme_menu(self):
        self.theme_menu.clear()
        for i, t in enumerate(THEMES):
            act = QAction(t.name, self)
            act.triggered.connect(lambda _=False, idx=i: self._apply_theme(idx))
            self.theme_menu.addAction(act)

    def _apply_theme(self, idx: int):
        theme = THEMES[idx]
        self.test.set_theme(theme)
        self.theme_idx = idx
        self.setWindowTitle(f"Typemaster — {theme.name}")

    def _reset_test(self):
        self.test.set_text(load_default_text())

    def _load_text_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open text", "", "Text Files (*.txt)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip().replace("\r\n", "\n")
        self.test.set_text(content)

    def _on_test_finished(self, wpm: float, acc: float, dur: float, weak_keys: dict):
        insert_result(self.user_id, wpm, acc, dur, json.dumps(weak_keys))
        self.setWindowTitle(f"Typemaster — WPM {wpm:.1f}, Acc {acc:.1f}%")

    # --- Dialogs ---
    def _open_weakkeys(self):
        ranked = self.test.state.weak_keys_ranked()
        WeakKeysDialog(ranked, self).exec()

    def _open_session(self):
        dlg = SessionEditor(self)
        if dlg.exec():
            cfg = dlg.result_config
            if cfg is None:
                return
            text = load_default_text()
            if cfg["text_path"]:
                try:
                    with open(cfg["text_path"], "r", encoding="utf-8") as f:
                        text = f.read().strip().replace("\r\n", "\n")
                except Exception as e:
                    QMessageBox.warning(self, "Text", f"Failed to load text:\n{e}")
            self.test.configure_session(
                time_limit=cfg["time_limit"],
                include_punct=cfg["include_punct"],
                include_numbers=cfg["include_numbers"],
            )
            self.test.set_text(text)

    def _open_theme_editor(self):
        theme = THEMES[getattr(self, "theme_idx", DEFAULT_THEME_INDEX)]
        if ThemeEditor(theme, self).exec():
            self._rebuild_theme_menu()

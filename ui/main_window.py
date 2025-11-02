from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QToolBar,
    QMenu,
    QFileDialog,
    QMessageBox,
    QToolButton,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

import json

from ui.test_ui import TestUI
from ui.weakkeys_dialog import WeakKeysDialog
from ui.session_editor import SessionEditor
from ui.theme_editor import ThemeEditor

from app.themes import THEMES, DEFAULT_THEME_INDEX, load_custom_themes
from utils.file_handler import load_default_text
from utils.db_helper import upsert_user, insert_result

from core.threads import TextLoadWorker, Workers


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Typemaster")
        self.resize(1200, 720)

        # user / themes
        self.user_id = upsert_user("guest")
        load_custom_themes()
        self.theme_idx = DEFAULT_THEME_INDEX

        # ---- central widget: a single TestUI instance ----
        central = QWidget(self)
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        self.test = TestUI(self)
        self.test.set_text(load_default_text())
        if hasattr(self.test, "finished"):
            self.test.finished.connect(self._on_test_finished)
        lay.addWidget(self.test)
        self.setCentralWidget(central)

        # apply default theme
        self._apply_theme(DEFAULT_THEME_INDEX)

        # ---- actions / menus / toolbar ----
        self._create_actions()
        self._build_menus()
        self._build_toolbar()
        self._append_main_actions_to_toolbar()

    # ---------------- UI scaffolding ----------------

    def _create_actions(self):
        self.actStart = QAction("Start", self)
        self.actPause = QAction("Pause", self)
        self.actResume = QAction("Resume", self)
        self.actFinish = QAction("Finish", self)
        self.actLoad = QAction("Load text…", self)
        self.actWeak = QAction("Weak keys…", self)

        self.actStart.setShortcut("Ctrl+Enter")
        self.actPause.setShortcut("Ctrl+P")
        self.actResume.setShortcut("Ctrl+R")
        self.actFinish.setShortcut("Ctrl+F")
        self.actLoad.setShortcut("Ctrl+O")
        self.actWeak.setShortcut("Ctrl+W")

        self.actStart.triggered.connect(self._on_start)
        self.actPause.triggered.connect(self._on_pause)
        self.actResume.triggered.connect(self._on_resume)
        self.actFinish.triggered.connect(self._on_finish)
        self.actLoad.triggered.connect(self._on_load)
        self.actWeak.triggered.connect(self._open_weakkeys)

    def _build_menus(self):
        test_menu = self.menuBar().addMenu("&Test")
        test_menu.addAction(self.actStart)
        test_menu.addAction(self.actPause)
        test_menu.addAction(self.actResume)
        test_menu.addAction(self.actFinish)
        test_menu.addSeparator()
        test_menu.addAction(self.actLoad)
        test_menu.addAction(self.actWeak)

    def _build_toolbar(self):
        """Toolbar: themes, session, weak keys, theme editor, load, reset."""
        self.tb = QToolBar("Toolbar", self)
        self.tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.tb)

        # ---- Theme menu button (QToolButton to show a dropdown properly) ----
        self.theme_menu = QMenu("Themes", self)
        self._rebuild_theme_menu()

        theme_btn = QToolButton(self)
        theme_btn.setText("Theme")
        theme_btn.setIcon(QIcon("assets/logo.png"))
        theme_btn.setPopupMode(QToolButton.InstantPopup)
        theme_btn.setMenu(self.theme_menu)
        self.tb.addWidget(theme_btn)

        # Session editor
        act_session = QAction("Session…", self)
        act_session.triggered.connect(self._open_session)
        self.tb.addAction(act_session)

        # Weak keys dialog
        act_weak = QAction("Weak Keys…", self)
        act_weak.triggered.connect(self._open_weakkeys)
        self.tb.addAction(act_weak)

        # Theme editor
        act_theme_editor = QAction("Theme Editor…", self)
        act_theme_editor.triggered.connect(self._open_theme_editor)
        self.tb.addAction(act_theme_editor)

        # Load text (threaded)
        btn_load_text = QAction("Load text…", self)
        btn_load_text.triggered.connect(self._on_load)
        self.tb.addAction(btn_load_text)

        # Reset test
        reset = QAction("Reset test", self)
        reset.triggered.connect(self._reset_test)
        self.tb.addAction(reset)

    def _append_main_actions_to_toolbar(self):
        self.tb.addSeparator()
        for a in (self.actStart, self.actPause, self.actResume, self.actFinish):
            self.tb.addAction(a)

    # ---------------- Themes ----------------

    def _rebuild_theme_menu(self):
        self.theme_menu.clear()
        for i, t in enumerate(THEMES):
            act = QAction(t.name, self)
            act.triggered.connect(lambda _=False, idx=i: self._apply_theme(idx))
            self.theme_menu.addAction(act)

    def _apply_theme(self, idx: int):
        theme = THEMES[idx]
        self.theme_idx = idx

        # Apply to typing UI
        if hasattr(self.test, "set_theme"):
            self.test.set_theme(theme)

        # Apply to the whole window
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {theme.background};
                color: {theme.primary};
            }}
            QLabel#lblLine {{ color: {theme.primary}; }}
            QLabel#lblTimer {{ color: {theme.secondary}; }}
            QLabel#lblWPM   {{ color: {theme.accent}; }}
            QLabel#lblAcc   {{ color: {theme.secondary}; }}
            """
        )

        self.setWindowTitle(f"Typemaster — {theme.name}")

    def _open_theme_editor(self):
        """Open the theme editor, then refresh theme menu after closing."""
        theme = THEMES[getattr(self, "theme_idx", DEFAULT_THEME_INDEX)]
        dlg = ThemeEditor(theme, self)
        if dlg.exec():
            # If ThemeEditor mutates THEMES or saved themes, rebuild menu.
            self._rebuild_theme_menu()

    # ---------------- Test control ----------------

    def _on_start(self):
        text = getattr(self.test, "current_text", None) or load_default_text()
        if hasattr(self.test, "start_test"):
            self.test.start_test(text)
        else:
            self.test.set_text(text)

    def _on_pause(self):
        if hasattr(self.test, "pause_test"):
            self.test.pause_test()

    def _on_resume(self):
        if hasattr(self.test, "resume_test"):
            self.test.resume_test()

    def _on_finish(self):
        if hasattr(self.test, "finish_test"):
            self.test.finish_test()

    def _reset_test(self):
        self.test.set_text(load_default_text())

    # ---------------- Loading text (threaded) ----------------

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open text", "", "Text Files (*.txt);;All files (*)"
        )
        if not path:
            return
        worker = TextLoadWorker(path)
        worker.signals.loaded.connect(self._on_loaded_text)
        worker.signals.failed.connect(self._on_load_failed)
        Workers.pool.start(worker)

    def _on_loaded_text(self, data: str):
        data = (data or "").strip().replace("\r\n", "\n")
        self.test.set_text(data)
        if hasattr(self.test, "start_test"):
            self.test.start_test(data)
        self.test.current_text = data

    def _on_load_failed(self, msg: str):
        QMessageBox.warning(self, "Load Text", f"Failed to load text:\n{msg}")

    # ---------------- Finish hook ----------------

    def _on_test_finished(self, wpm: float, acc: float, dur: float, weak_keys: dict):
        """Called when a typing session finishes; persists and updates title."""
        try:
            insert_result(self.user_id, wpm, acc, dur, json.dumps(weak_keys))
        except Exception as e:
            # don’t crash on DB issues—just log/print
            print("insert_result failed:", e)
        self.setWindowTitle(f"Typemaster — WPM {wpm:.1f}, Acc {acc:.1f}%")

    # ---------------- Dialogs ----------------

    def _open_weakkeys(self):
        ranked = None
        if hasattr(self.test, "state") and hasattr(self.test.state, "weak_keys_ranked"):
            ranked = self.test.state.weak_keys_ranked()
        elif hasattr(self.test, "weak") and hasattr(self.test.weak, "snapshot"):
            snap = self.test.weak.snapshot()
            rows = []
            for key, score in snap.items():
                hits = max(1, int(score))
                miss = int(score // 2)
                attempts = hits + miss
                miss_rate = (miss / attempts) if attempts else 0.0
                rows.append((key, miss_rate, hits, miss))
            rows.sort(key=lambda r: r[1], reverse=True)
            ranked = rows
        else:
            ranked = []

        WeakKeysDialog(ranked, self).exec()

    def _open_session(self):
        dlg = SessionEditor(self)
        if dlg.exec():
            cfg = dlg.result_config
            if cfg is None:
                return
            text = load_default_text()
            if cfg.get("text_path"):
                try:
                    with open(cfg["text_path"], "r", encoding="utf-8") as f:
                        text = f.read().strip().replace("\r\n", "\n")
                except Exception as e:
                    QMessageBox.warning(self, "Text", f"Failed to load text:\n{e}")
            if hasattr(self.test, "configure_session"):
                self.test.configure_session(
                    time_limit=cfg.get("time_limit"),
                    include_punct=cfg.get("include_punct"),
                    include_numbers=cfg.get("include_numbers"),
                )
            self.test.set_text(text)

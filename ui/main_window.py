# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenu, QFileDialog, QMessageBox,
    QToolButton, QPushButton
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

import json
import pathlib, random

from ui.test_ui import TestUI
from ui.weakkeys_dialog import WeakKeysDialog
from ui.widgets.session_dialog import SessionDialog

from app.themes import THEMES, DEFAULT_THEME_INDEX, load_custom_themes
from utils.file_handler import load_default_text
from utils.db_helper import upsert_user, insert_result
from core.threads import TextLoadWorker, Workers


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Typemaster")
        self.resize(1200, 720)

        self.user_id = upsert_user("guest")
        load_custom_themes()
        self.theme_idx = DEFAULT_THEME_INDEX

        root = QWidget(self)
        root_v = QVBoxLayout(root)
        root_v.setContentsMargins(16, 40, 16, 16)   # ← Increased top margin
        root_v.setSpacing(24)                      # ← Slightly more spacing

        self._build_top_bar(root_v)

        self.test = TestUI(self)
        self.test.set_text(load_default_text())
        if hasattr(self.test, "finished"):
            self.test.finished.connect(self._on_test_finished)

        test_h = QHBoxLayout()
        test_h.addStretch(1)
        test_h.addWidget(self.test, 1)
        test_h.addStretch(1)
        root_v.addLayout(test_h, 1)
        self.setCentralWidget(root)

        # Remove menu bar
        self.menuBar().setVisible(False)

        # apply theme
        self._apply_theme(DEFAULT_THEME_INDEX)


    # ---------------- Floating Top Bar ----------------
    def _build_top_bar(self, parent_layout):
        from PySide6.QtWidgets import QStyle

        bar = QWidget(self)
        bar.setObjectName("TopBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 16, 14, 16)   # <--- moved down visually
        h.setSpacing(10)

        # Theme dropdown (clean, no arrow)
        self.theme_menu = QMenu(self)
        self._rebuild_theme_menu()

        theme_btn = QToolButton(bar)
        theme_btn.setText("Theme")
        theme_btn.setObjectName("TopBtn")
        theme_btn.setMenu(self.theme_menu)
        theme_btn.setPopupMode(QToolButton.InstantPopup)

        # Remove menu indicator arrow
        theme_btn.setStyleSheet(
            "QToolButton::menu-indicator { image: none; width:0; height:0; }"
        )

        h.addWidget(theme_btn)

        # Session
        btn_session = QPushButton("Session…", bar)
        btn_session.clicked.connect(self._open_session)
        btn_session.setObjectName("TopBtn")
        h.addWidget(btn_session)

        # Weak Keys
        btn_weak = QPushButton("Weak Keys…", bar)
        btn_weak.clicked.connect(self._open_weakkeys)
        btn_weak.setObjectName("TopBtn")
        h.addWidget(btn_weak)

        # Load Text
        btn_load = QPushButton("Load text…", bar)
        btn_load.clicked.connect(self._on_load)
        btn_load.setObjectName("TopBtn")
        h.addWidget(btn_load)

        # Reset
        btn_reset = QPushButton("Reset test", bar)
        btn_reset.clicked.connect(self._reset_test)
        btn_reset.setObjectName("TopBtn")
        h.addWidget(btn_reset)

        h.addStretch(1)  # Push Start/Stop controls to right

        # Controls
        self.btnStart = QPushButton("Start", bar)
        self.btnPause = QPushButton("Pause", bar)
        self.btnResume = QPushButton("Resume", bar)
        self.btnFinish = QPushButton("Finish", bar)

        for button, handler in [
            (self.btnStart, self._on_start),
            (self.btnPause, self._on_pause),
            (self.btnResume, self._on_resume),
            (self.btnFinish, self._on_finish),
        ]:
            button.clicked.connect(handler)
            button.setObjectName("TopBtn")
            h.addWidget(button)

        parent_layout.addWidget(bar)

        # --- Top Bar Styling ---
        self._topbar_qss = """
        QWidget#TopBar {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
        }
        QPushButton#TopBtn, QToolButton#TopBtn {
            background: transparent;
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 9px;
            padding: 6px 12px;
        }
        QPushButton#TopBtn:hover, QToolButton#TopBtn:hover {
            border-color: rgba(255,255,255,0.32);
            background: rgba(255,255,255,0.06);
        }
        QToolButton::menu-indicator {
            image: none !important;  /* Ensure arrow is fully hidden */
            width: 0px;
            height: 0px;
        }
        """

    # ---------------- Menus ----------------
    def _create_actions(self):
        self.actStart = QAction("Start", self)
        self.actPause = QAction("Pause", self)
        self.actResume = QAction("Resume", self)
        self.actFinish = QAction("Finish", self)
        self.actLoad = QAction("Load text…", self)
        self.actWeak = QAction("Weak keys…", self)

        self.actStart.triggered.connect(self._on_start)
        self.actPause.triggered.connect(self._on_pause)
        self.actResume.triggered.connect(self._on_resume)
        self.actFinish.triggered.connect(self._on_finish)
        self.actLoad.triggered.connect(self._on_load)
        self.actWeak.triggered.connect(self._open_weakkeys)

    def _build_menus(self):
        menu = self.menuBar().addMenu("Test")
        menu.addAction(self.actStart)
        menu.addAction(self.actPause)
        menu.addAction(self.actResume)
        menu.addAction(self.actFinish)
        menu.addSeparator()
        menu.addAction(self.actLoad)
        menu.addAction(self.actWeak)

    # ---------------- Themes ----------------
    def _rebuild_theme_menu(self):
        self.theme_menu.clear()
        for i, t in enumerate(THEMES):
            act = QAction(t.name, self)
            act.triggered.connect(lambda _, idx=i: self._apply_theme(idx))
            self.theme_menu.addAction(act)

    def _apply_theme(self, idx):
        theme = THEMES[idx]
        self.theme_idx = idx

        if hasattr(self.test, "set_theme"):
            self.test.set_theme(theme)

        self.setStyleSheet(
            f"""
            QWidget {{
                background: {theme.background};
                color: {theme.primary};
            }}
            QLabel#lblLine {{ color: {theme.primary}; }}
            QLabel#lblTimer, QLabel#lblAcc {{ color: {theme.secondary}; }}
            QLabel#lblWPM   {{ color: {theme.accent}; }}
            {self._topbar_qss}
            """
        )
        self.setWindowTitle(f"Typemaster — {theme.name}")

    # ---------------- Text Loading ----------------
    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open text", "", "Text (*.txt)")
        if not path:
            return
        worker = TextLoadWorker(path)
        worker.signals.loaded.connect(self._on_loaded_text)
        worker.signals.failed.connect(self._on_load_failed)
        Workers.pool.start(worker)

    def _on_loaded_text(self, data):
        data = (data or "").strip().replace("\r\n", "\n")
        self.test.set_text(data)
        self.test.start_test(data)
        self.test.current_text = data

    def _on_load_failed(self, msg):
        QMessageBox.warning(self, "Load Text", msg)

    # ---------------- Weak Keys ----------------
    def _open_weakkeys(self):
        ranked = []
        try:
            snap = self.test.weak.snapshot()
            for key, score in snap.items():
                hits = max(1, int(score))
                miss = int(score // 2)
                attempts = hits + miss
                miss_rate = miss / attempts if attempts else 0
                ranked.append((key, miss_rate, hits, miss))
            ranked.sort(key=lambda r: r[1], reverse=True)
        except:
            pass
        WeakKeysDialog(ranked, self).exec()

    # ---------------- Session Handling ----------------
    def _open_session(self):
        dlg = SessionDialog(self)
        if not dlg.exec():
            return
        cfg = dlg.config

        text = self._assemble_text(cfg["source"])

        if hasattr(self.test, "configure_session"):
            self.test.configure_session(cfg["time_limit"])

        self.test.set_text(text)
        self.test.current_text = text
        self.test.start_test(text)

    # ---------------- Endless / Source Logic ----------------
    def _load_blocks(self, filename):
        p = pathlib.Path("assets/texts") / filename
        if not p.exists():
            return []
        txt = p.read_text(encoding="utf-8").strip()
        return [b.strip() for b in txt.split("\n\n") if b.strip()]

    def _endless(self, blocks, min_chars=50000):
        if not blocks:
            return ""
        out = []
        total = 0
        pool = blocks[:]
        random.shuffle(pool)
        i = 0
        while total < min_chars:
            out.append(pool[i])
            total += len(pool[i]) + 2
            i += 1
            if i >= len(pool):
                random.shuffle(pool)
                i = 0
        return "\n\n".join(out)

    def _assemble_text(self, source):
        file_map = {
            "Paragraph":     "paragraph.txt",
            "Quotes":        "quotes.txt",
            "Code Snippets": "codesnippets.txt",
            "Numbers":       "numbers.txt",       # natural text with numbers
            "Punctuation":   "punctuation.txt",   # natural text with punctuation
        }

        filename = file_map.get(source, "paragraph.txt")
        blocks = self._load_blocks(filename)

        if source == "Paragraph":
            return self._endless(blocks)  # infinite paragraphs

        # single-block random for the others
        return random.choice(blocks) if blocks else ""

    # ---------------- Controls ----------------
    def _on_start(self):
        self.test.start_test(self.test.current_text or load_default_text())
    def _on_pause(self):
        self.test.pause_test()
    def _on_resume(self):
        self.test.resume_test()
    def _on_finish(self):
        self.test.finish_test()
    def _reset_test(self):
        self.test.set_text(load_default_text())

    # ---------------- Save Result ----------------
    def _on_test_finished(self, wpm, acc, dur, weak):
        try:
            insert_result(self.user_id, wpm, acc, dur, json.dumps(weak))
        except:
            pass
        self.setWindowTitle(f"Typemaster — {wpm:.1f} WPM")

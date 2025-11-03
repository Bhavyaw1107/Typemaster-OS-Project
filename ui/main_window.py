# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenu, QFileDialog, QMessageBox,
    QToolButton, QPushButton
)
from PySide6.QtGui import QAction
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
        self._waiting_for_autostart = False

        root = QWidget(self)
        root_v = QVBoxLayout(root)
        root_v.setContentsMargins(16, 40, 16, 16)
        root_v.setSpacing(24)
        self._build_top_bar(root_v)

        # --- Test UI setup ---
        self.test = TestUI(self)
        paragraph_text = self._assemble_text("Paragraph")
        self.test.set_text(paragraph_text)
        self.test.configure_session(time_limit=30)
        self.test.current_text = paragraph_text

        # Connect signals
        if hasattr(self.test, "finished"):
            self.test.finished.connect(self._on_test_finished)
        if hasattr(self.test, "firstKey"):
            self.test.firstKey.connect(self._on_first_key)

        test_h = QHBoxLayout()
        test_h.addStretch(1)
        test_h.addWidget(self.test, 1)
        test_h.addStretch(1)
        root_v.addLayout(test_h, 1)
        self.setCentralWidget(root)

        # Prevent main window from stealing keyboard focus
        # ensures TestUI is the focus receiver
        try:
            self.setFocusPolicy(Qt.NoFocus)
        except Exception:
            pass

        # Make sure TestUI has focus so it receives the first keypress
        try:
            self.test.setFocus()
        except Exception:
            pass

        # Hide menu bar & apply theme
        self.menuBar().setVisible(False)
        self._apply_theme(DEFAULT_THEME_INDEX)

        # Enter autostart immediately (like Monkeytype)
        self._enter_autostart_mode()

    # ---------------- Top Bar ----------------
    def _build_top_bar(self, parent_layout):
        bar = QWidget(self)
        bar.setObjectName("TopBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 16, 14, 16)
        h.setSpacing(10)

        self.theme_menu = QMenu(self)
        self._rebuild_theme_menu()
        theme_btn = QToolButton(bar)
        theme_btn.setText("Theme")
        theme_btn.setObjectName("TopBtn")
        theme_btn.setMenu(self.theme_menu)
        theme_btn.setPopupMode(QToolButton.InstantPopup)
        theme_btn.setStyleSheet("QToolButton::menu-indicator { image: none; width:0; height:0; }")
        # Important: prevent theme button from taking keyboard focus
        theme_btn.setFocusPolicy(Qt.NoFocus)
        h.addWidget(theme_btn)

        # Session / Weak Keys / Load / Reset
        btn_session = QPushButton("Session…", bar)
        btn_session.clicked.connect(self._open_session)
        btn_session.setObjectName("TopBtn")
        btn_session.setFocusPolicy(Qt.NoFocus)   # << prevent focus
        h.addWidget(btn_session)

        btn_weak = QPushButton("Weak Keys…", bar)
        btn_weak.clicked.connect(self._open_weakkeys)
        btn_weak.setObjectName("TopBtn")
        btn_weak.setFocusPolicy(Qt.NoFocus)
        h.addWidget(btn_weak)

        btn_load = QPushButton("Load text…", bar)
        btn_load.clicked.connect(self._on_load)
        btn_load.setObjectName("TopBtn")
        btn_load.setFocusPolicy(Qt.NoFocus)
        h.addWidget(btn_load)

        btn_reset = QPushButton("Reset test", bar)
        btn_reset.clicked.connect(self._reset_test)
        btn_reset.setObjectName("TopBtn")
        btn_reset.setFocusPolicy(Qt.NoFocus)
        h.addWidget(btn_reset)

        h.addStretch(1)

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
            button.setFocusPolicy(Qt.NoFocus)   # << prevent focus
            h.addWidget(button)

        parent_layout.addWidget(bar)

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
        QToolButton::menu-indicator { image: none !important; width: 0px; height: 0px; }
        """

    # ---------------- Theme ----------------
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
            QWidget {{ background: {theme.background}; color: {theme.primary}; }}
            QLabel#lblLine {{ color: {theme.primary}; }}
            QLabel#lblTimer, QLabel#lblAcc {{ color: {theme.secondary}; }}
            QLabel#lblWPM   {{ color: {theme.accent}; }}
            {self._topbar_qss}
            """
        )
        self.setWindowTitle(f"Typemaster — {theme.name}")

    # ---------------- Autostart Flow ----------------
    def _enter_autostart_mode(self):
        self._waiting_for_autostart = True
        if hasattr(self.test, "enable_autostart"):
            self.test.enable_autostart(True)
        self.setWindowTitle("Typemaster — Press any key to start...")
        # ensure test has focus while waiting for autostart
        try:
            self.test.setFocus()
        except Exception:
            pass

    def _exit_autostart_mode(self):
        self._waiting_for_autostart = False
        if hasattr(self.test, "enable_autostart"):
            self.test.enable_autostart(False)
        theme_name = THEMES[self.theme_idx].name if 0 <= self.theme_idx < len(THEMES) else "Typemaster"
        self.setWindowTitle(f"Typemaster — {theme_name}")

    def _on_first_key(self, nk: str):
        """Start typing session when first key is pressed."""
        if not self._waiting_for_autostart:
            return
        self._exit_autostart_mode()
        self.test.start_test(self.test.current_text)
        self.test.type_programmatically(nk)

    # ---------------- Session / Controls ----------------
    def _open_session(self):
        dlg = SessionDialog(self)
        if not dlg.exec():
            return
        cfg = dlg.config
        text = self._assemble_text(cfg["source"])
        self.test.configure_session(cfg["time_limit"])
        self.test.set_text(text)
        self.test.current_text = text
        self._enter_autostart_mode()

    def _on_start(self):
        self._enter_autostart_mode()

    def _on_pause(self):
        self.test.pause_test()

    def _on_resume(self):
        self.test.resume_test()

    def _on_finish(self):
        self.test.finish_test()

    def _reset_test(self):
        paragraph_text = self._assemble_text("Paragraph")
        self.test.reset_test(paragraph_text)
        self.test.configure_session(30)
        self.test.current_text = paragraph_text
        self._enter_autostart_mode()

    # ---------------- Text Loading ----------------
    def _on_load(self):
        """
        Open a file dialog and load a text file on a background worker.
        Ensures _on_loaded_text or _on_load_failed is called when done.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Open text", "", "Text (*.txt)")
        if not path:
            return
        worker = TextLoadWorker(path)
        worker.signals.loaded.connect(self._on_loaded_text)
        worker.signals.failed.connect(self._on_load_failed)
        Workers.pool.start(worker)

    def _on_loaded_text(self, data):
        """
        Called by the TextLoadWorker when the file is loaded successfully.
        Sets the text in TestUI, starts the test immediately and disables autostart.
        """
        data = (data or "").strip().replace("\r\n", "\n")
        # set and start test with loaded content
        if hasattr(self.test, "set_text"):
            self.test.set_text(data)
            self.test.current_text = data
        try:
            # start right away (user likely expects auto-start on load)
            if hasattr(self.test, "start_test"):
                self.test.start_test(data)
        except Exception:
            pass
        # ensure autostart not left on
        self._waiting_for_autostart = False
        if hasattr(self.test, "enable_autostart"):
            self.test.enable_autostart(False)
        self._exit_autostart_mode()

    def _on_load_failed(self, msg):
        QMessageBox.warning(self, "Load Text", msg)

    # ---------------- Text Source ----------------
    def _load_blocks(self, filename):
        p = pathlib.Path("assets/texts") / filename
        if not p.exists():
            return []
        txt = p.read_text(encoding="utf-8").strip()
        return [b.strip() for b in txt.split("\n\n") if b.strip()]

    def _endless(self, blocks, min_chars=50000):
        if not blocks:
            return ""
        out, total, pool, i = [], 0, blocks[:], 0
        random.shuffle(pool)
        while total < min_chars:
            out.append(pool[i])
            total += len(pool[i]) + 2
            i = (i + 1) % len(pool)
            if i == 0:
                random.shuffle(pool)
        return "\n\n".join(out)

    def _assemble_text(self, source):
        file_map = {
            "Paragraph": "paragraph.txt",
            "Quotes": "quotes.txt",
            "Code Snippets": "codesnippets.txt",
            "Numbers": "numbers.txt",
            "Punctuation": "punctuation.txt",
        }
        filename = file_map.get(source, "paragraph.txt")
        blocks = self._load_blocks(filename)
        if source == "Paragraph":
            return self._endless(blocks)
        return random.choice(blocks) if blocks else ""

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

    # ---------------- Save Result ----------------
    def _on_test_finished(self, wpm, acc, dur, weak):
        try:
            insert_result(self.user_id, wpm, acc, dur, json.dumps(weak))
        except:
            pass
        self.setWindowTitle(f"Typemaster — {wpm:.1f} WPM")

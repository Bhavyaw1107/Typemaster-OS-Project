from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QTimer
from PySide6.QtGui import QKeyEvent
import pyqtgraph as pg
import re

from app.state import TestState
from app.audio import AudioEngine
from app.themes import THEMES, DEFAULT_THEME_INDEX
from app.calculation import compute_wpm_series, smooth
from utils.graph_helper import setup_wpm_plot, update_curve
from utils.file_handler import load_stakeholders
from ui.widgets.typing_area import TypingArea

class TestUI(QWidget):
    finished = Signal(float, float, float, dict)  # wpm, acc, dur, weak_keys

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_idx = DEFAULT_THEME_INDEX
        self.theme = THEMES[self.theme_idx]
        self.state = TestState()
        self.audio = AudioEngine()
        self.audio.load_from_theme(self.theme)

        # Session config
        self._time_limit = None
        self._include_punct = True
        self._include_numbers = True
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._maybe_timeout)
        self._tick.start(100)

        self._build_ui()
        self.apply_theme()
        self._intro_visible(True)

    # ---- Session configuration ----
    def configure_session(self, *, time_limit=None, include_punct=True, include_numbers=True):
        self._time_limit = time_limit
        self._include_punct = include_punct
        self._include_numbers = include_numbers

    def _preprocess_text(self, text: str) -> str:
        t = text
        if not self._include_punct:
            t = re.sub(r"[^\w\s]", "", t)
        if not self._include_numbers:
            t = re.sub(r"\d", "", t)
        return t

    # ---- UI ----
    def _build_ui(self):
        self.setObjectName("TestUI")
        self.setFocusPolicy(Qt.StrongFocus)

        self.root = QHBoxLayout(self)
        self.root.setContentsMargins(24, 24, 24, 24)
        self.root.setSpacing(18)

        # Left column
        left = QVBoxLayout()
        left.setSpacing(12)
        self.typing = TypingArea(lambda: self.state, lambda: self.theme)
        left.addWidget(self.typing, stretch=1)
        self.stats = QLabel("WPM: 0   Accuracy: 100%   Keys: 0")
        self.stats.setObjectName("StatsLabel")
        left.addWidget(self.stats)
        self.root.addLayout(left, stretch=3)

        # Right column
        right = QVBoxLayout()
        self.plot = pg.PlotWidget()
        self.curve = setup_wpm_plot(self.plot, self.theme.graph_line)
        right.addWidget(self.plot, stretch=1)
        self.weakkeys_label = QLabel("Weak keys: —")
        right.addWidget(self.weakkeys_label)
        self.root.addLayout(right, stretch=2)

        # Intro overlay with stakeholders
        data = load_stakeholders()
        self.overlay = QFrame(self)
        self.overlay.setObjectName("IntroOverlay")
        self.overlay.setFrameShape(QFrame.NoFrame)
        ovl = QVBoxLayout(self.overlay)
        ovl.setContentsMargins(32, 32, 32, 32)

        title = QLabel(data.get("title", "Welcome to Typemaster"))
        title.setProperty("tm", "title")
        ovl.addWidget(title)

        subtitle = QLabel(data.get("subtitle", "Press any key to start."))
        subtitle.setWordWrap(True)
        ovl.addWidget(subtitle)

        stake = data.get("stakeholders", [])
        if stake:
            hdr = QLabel("Stakeholders")
            hdr.setStyleSheet("font-weight: 600; margin-top: 12px;")
            ovl.addWidget(hdr)
            for person in stake:
                line = QLabel(f"• {person.get('name','')} — {person.get('role','')}"
                              + (f" ({person.get('note')})" if person.get('note') else ""))
                line.setWordWrap(True)
                ovl.addWidget(line)

        self.overlay.setGraphicsEffect(QGraphicsOpacityEffect(self.overlay))
        self.overlay_effect = self.overlay.graphicsEffect()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.overlay.setGeometry(self.rect())

    def _intro_visible(self, vis: bool):
        self.overlay.setVisible(True)
        anim = QPropertyAnimation(self.overlay_effect, b"opacity")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(1.0 if vis else 0.0)
        anim.setEndValue(0.0 if vis else 1.0)
        anim.finished.connect(lambda: self.overlay.setVisible(vis))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    # ---- Set text / theme ----
    def set_text(self, text: str):
        self.state.reset(self._preprocess_text(text))
        self.update()

    def set_theme(self, theme):
        self.theme = theme
        self.apply_theme()
        self.audio.load_from_theme(theme)

    def apply_theme(self):
        pal_css = f"""
        QWidget#TestUI {{
            background: {self.theme.bg};
            color: {self.theme.text};
        }}
        QLabel#StatsLabel {{ font-size: 18px; }}
        """
        self.setStyleSheet(pal_css)
        self.plot.setBackground(None)
        self.curve.setPen({'color': self.theme.graph_line, 'width': 2.5})

    # ---- Typing logic ----
    def keyPressEvent(self, event: QKeyEvent):
        key = event.text()
        if not key:
            return

        if not self.state.is_running and self.state.position == 0:
            self.state.start()
            self._intro_visible(False)

        idx = self.state.position
        if idx >= len(self.state.target_text):
            return

        expected = self.state.target_text[idx]
        is_correct = (key == expected)

        self.state.mark_key(key, is_correct)
        self.audio.play_key()
        (self.audio.play_ok() if is_correct else self.audio.play_err())
        if is_correct:
            self.state.position += 1

        self._update_stats_and_graph()

        if self.state.position >= len(self.state.target_text):
            self.state.stop()
            self._update_stats_and_graph(final=True)

        self.typing.update()

    # ---- Time limit ----
    def _maybe_timeout(self):
        if self._time_limit and self.state.is_running:
            if self.state.duration() >= self._time_limit:
                self.state.stop()
                self._update_stats_and_graph(final=True)

    # ---- Stats/graph ----
    def _update_stats_and_graph(self, final: bool = False):
        st = self.state
        flags = [k.correct for k in st.keystrokes]
        times = [k.t for k in st.keystrokes]
        wpm_series = smooth(compute_wpm_series(flags, times))
        if wpm_series:
            update_curve(self.curve, wpm_series)

        tl = f"  •  Time: {self._time_limit - int(st.duration())}s" if (self._time_limit and st.is_running) else ""
        self.stats.setText(f"WPM: {st.wpm():.1f}   Accuracy: {st.accuracy():.1f}%   Keys: {len(st.keystrokes)}{tl}")

        wk = st.weak_keys_ranked()[:6]
        self.weakkeys_label.setText("Weak keys: " + (", ".join(f"{k}:{int(mr*100)}%" for k, mr, _, _ in wk) if wk else "—"))

        if final:
            self.finished.emit(st.wpm(), st.accuracy(), st.duration(), st.weak_keys)

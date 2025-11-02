from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QTimer
from PySide6.QtGui import QKeyEvent
import pyqtgraph as pg
import random
import re
import time

from app.state import TestState
from app.audio import AudioEngine
from app.themes import THEMES, DEFAULT_THEME_INDEX
from app.calculation import rolling_wpm, smooth
from utils.graph_helper import setup_wpm_plot, update_curve
from utils.file_handler import load_stakeholders
from ui.widgets.typing_area import TypingArea

# A compact, common English word list (you can expand later)
_WORDS = [
    "the","be","to","of","and","a","in","that","have","I",
    "it","for","not","on","with","he","as","you","do","at",
    "this","but","his","by","from","they","we","say","her","she",
    "or","an","will","my","one","all","would","there","their",
    "what","so","up","out","if","about","who","get","which","go",
    "me","when","make","can","like","time","no","just","him","know",
    "take","people","into","year","your","good","some","could","them","see",
    "other","than","then","now","look","only","come","its","over","think",
    "also","back","after","use","two","how","our","work","first","well",
    "way","even","new","want","because","any","these","give","day","most"
]

def _make_words_stream(n_words: int = 60) -> str:
    return " ".join(random.choice(_WORDS) for _ in range(n_words)) + " "

class TestUI(QWidget):
    finished = Signal(float, float, float, dict)  # wpm, acc, dur, weak_keys

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_idx = DEFAULT_THEME_INDEX
        self.theme = THEMES[self.theme_idx]
        self.state = TestState()
        self.audio = AudioEngine()
        self.audio.load_from_theme(self.theme)

        # session options
        self._time_limit = None
        self._include_punct = True
        self._include_numbers = True

        # timers
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._maybe_timeout)
        self._tick.start(100)

        self._build_ui()
        self.apply_theme()

        # initial content: words mode
        self.set_text(_make_words_stream())
        self._intro_visible(True)

    # ---------- Session configuration ----------
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

    # ---------- UI ----------
    def _build_ui(self):
        self.setObjectName("TestUI")
        self.setFocusPolicy(Qt.StrongFocus)

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        # Left: typing
        left = QVBoxLayout(); left.setSpacing(12)
        self.typing = TypingArea(lambda: self.state, lambda: self.theme)
        left.addWidget(self.typing, stretch=1)
        self.stats = QLabel("WPM: 0   Accuracy: 100%   Keys: 0")
        self.stats.setObjectName("StatsLabel")
        left.addWidget(self.stats)
        root.addLayout(left, stretch=3)

        # Right: graph + weak keys
        right = QVBoxLayout()
        self.plot = pg.PlotWidget()
        self.curve = setup_wpm_plot(self.plot, self.theme.graph_line)
        right.addWidget(self.plot, stretch=1)
        self.weakkeys_label = QLabel("Weak keys: —")
        right.addWidget(self.weakkeys_label)
        root.addLayout(right, stretch=2)

        # Intro overlay (stakeholders)
        data = load_stakeholders()
        self.overlay = QFrame(self); self.overlay.setObjectName("IntroOverlay")
        self.overlay.setFrameShape(QFrame.NoFrame)
        ovl = QVBoxLayout(self.overlay); ovl.setContentsMargins(32, 32, 32, 32)
        title = QLabel(data.get("title", "Welcome to Typemaster")); title.setProperty("tm", "title")
        subtitle = QLabel(data.get("subtitle", "Press any key to start.")); subtitle.setWordWrap(True)
        ovl.addWidget(title); ovl.addWidget(subtitle)
        stake = data.get("stakeholders", [])
        if stake:
            hdr = QLabel("Stakeholders"); hdr.setStyleSheet("font-weight: 600; margin-top: 12px;")
            ovl.addWidget(hdr)
            for person in stake:
                line = QLabel(f"• {person.get('name','')} — {person.get('role','')}"
                              + (f" ({person.get('note')})" if person.get('note') else ""))
                line.setWordWrap(True); ovl.addWidget(line)
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

    # ---------- Content ----------
    def set_text(self, text: str):
        self.state.reset(self._preprocess_text(text))
        self.typing.update()

    def set_theme(self, theme):
        self.theme = theme
        self.apply_theme()
        self.audio.load_from_theme(theme)

    def apply_theme(self):
        css = f"""
        QWidget#TestUI {{
            background: {self.theme.bg};
            color: {self.theme.text};
        }}
        QLabel#StatsLabel {{ font-size: 18px; }}
        """
        self.setStyleSheet(css)
        self.plot.setBackground(None)
        self.curve.setPen({'color': self.theme.graph_line, 'width': 2.5})

    # ---------- Typing engine (monkeytype-like) ----------
    def keyPressEvent(self, e: QKeyEvent):
        key_text = e.text()
        key = e.key()
        mods = e.modifiers()

        # ignore nav keys / tab
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Tab):
            return

        # quick controls
        if key == Qt.Key_Escape:
            self._reset_words()
            return
        if (mods & Qt.ControlModifier) and key in (Qt.Key_R,):
            self._reset_words()
            return

        # start on first printable key
        if not self.state.is_running and self.state.position == 0 and key_text:
            self.state.start()
            self._intro_visible(False)

        # no text? (e.g., function keys)
        if key_text == "" and key != Qt.Key_Backspace and key != Qt.Key_Space:
            return

        pos = self.state.position

        # Backspace behavior: allow correcting across words
        if key == Qt.Key_Backspace:
            if pos > 0 and self.state.is_running:
                # remove last typed char
                self.state.position -= 1
                # also drop last keystroke mark to repaint state accurately
                if self.state.keystrokes:
                    self.state.keystrokes.pop()
                self.typing.update()
                self._update_stats_and_graph()
            return

        # Normal char or space
        if pos >= len(self.state.target_text):
            return

        expected = self.state.target_text[pos]

        # Monkeytype behavior: space advances to next word; if still within word,
        # treat as a wrong char if expected wasn't a space.
        ch = key_text
        if key == Qt.Key_Space:
            ch = " "

        is_correct = (ch == expected)
        self.state.mark_key(ch, is_correct)
        self.audio.play_key()
        (self.audio.play_ok() if is_correct else self.audio.play_err())

        # advance one position always (like monkeytype), even if wrong; you can backspace to fix
        self.state.position += 1

        # When we reach end of buffer, append more words (infinite stream)
        if self.state.position > len(self.state.target_text) - 20:
            self.state.target_text += _make_words_stream(20)

        self._update_stats_and_graph()
        self.typing.update()

    def _reset_words(self):
        self.state.stop()
        self.state.reset(_make_words_stream())
        self._intro_visible(True)
        self.typing.update()
        self._update_stats_and_graph()

    # ---------- Time limit ----------
    def _maybe_timeout(self):
        if self._time_limit and self.state.is_running:
            if self.state.duration() >= self._time_limit:
                self.state.stop()
                self._update_stats_and_graph(final=True)

    # ---------- Metrics / graph ----------
    def _update_stats_and_graph(self, final: bool = False):
        st = self.state
        flags = [k.correct for k in st.keystrokes]
        times = [k.t for k in st.keystrokes]

        # Rolling WPM for smooth “live” feel
        wpm_series = rolling_wpm(flags, times, window_sec=10.0)
        if wpm_series:
            update_curve(self.curve, smooth(wpm_series, 0.3))

        # Overall stats
        hits = sum(1 for f in flags if f)
        acc = (hits / len(flags) * 100.0) if flags else 100.0
        live_wpm = wpm_series[-1] if wpm_series else 0.0
        tl = f"  •  Time: {self._time_limit - int(st.duration())}s" if (self._time_limit and st.is_running) else ""
        self.stats.setText(f"WPM: {live_wpm:.1f}   Accuracy: {acc:.1f}%   Keys: {len(flags)}{tl}")

        # Weak keys (top 6 by miss rate)
        wk = st.weak_keys_ranked()[:6]
        self.weakkeys_label.setText("Weak keys: " + (", ".join(f"{k}:{int(mr*100)}%" for k, mr, _, _ in wk) if wk else "—"))

        if final:
            self.finished.emit(live_wpm, acc, st.duration(), st.weak_keys)

# ui/test_ui.py
from __future__ import annotations
from collections import deque

from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy

from services.typing_engine import TypingEngine
from services.weakkeys import WeakKeys
from core.chrono import RealtimeTimer
from ui.session_summary import SessionSummary


class TestUI(QWidget):
    # main window can connect to this if needed
    finished = Signal(float, float, float, dict)  # wpm, acc%, secs, weakkeys_snapshot

    def __init__(self, parent=None):
        super().__init__(parent)

        # ===== Layout (centered, no wasted space) =====
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 30, 0, 30)
        root.setSpacing(28)

        # --- stats row (centered) ---
        stats = QHBoxLayout()
        stats.setSpacing(40)

        self.lblTimer = QLabel("0.0s", self)
        self.lblTimer.setObjectName("lblTimer")
        self.lblTimer.setAlignment(Qt.AlignCenter)

        self.lblWPM = QLabel("0.0 WPM", self)
        self.lblWPM.setObjectName("lblWPM")
        self.lblWPM.setAlignment(Qt.AlignCenter)

        self.lblAcc = QLabel("100% ACC", self)
        self.lblAcc.setObjectName("lblAcc")
        self.lblAcc.setAlignment(Qt.AlignCenter)

        for lab in (self.lblTimer, self.lblWPM, self.lblAcc):
            stats.addWidget(lab)

        root.addLayout(stats)

        # --- typing line (HTML styled, centered, expands) ---
        self.lblLine = QLabel("", self)
        self.lblLine.setObjectName("lblLine")
        self.lblLine.setTextFormat(Qt.RichText)
        self.lblLine.setWordWrap(True)
        self.lblLine.setAlignment(Qt.AlignCenter)
        self.lblLine.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lblLine.setMinimumHeight(100)
        root.addWidget(self.lblLine, stretch=1)

        # ===== Engines / timers =====
        self.engine = TypingEngine("")
        self.weak = WeakKeys()

        # Real-time timer (100 ms)
        self.timer = RealtimeTimer(tick_ms=100, parent=self)
        self.timer.elapsedChanged.connect(self.on_elapsed_changed)

        # Metrics refresh @10 Hz
        self._ui_tick = QTimer(self)
        self._ui_tick.setInterval(100)
        self._ui_tick.timeout.connect(self.refresh_metrics)
        self._ui_tick.start()

        # Caret blink
        self._caret_on = True
        self._caret_timer = QTimer(self)
        self._caret_timer.setInterval(500)
        self._caret_timer.timeout.connect(self._toggle_caret)
        self._caret_timer.start()

        # State
        self._active_seconds = 0.0
        self._running = False
        self.current_text: str | None = None  # for MainWindow use

        # Buffers for post-run graph
        self._wpm_time = deque(maxlen=3600)  # ~6 min @ 10Hz
        self._wpm_vals = deque(maxlen=3600)

        # 3-line window tuning
        self._approx_chars_per_line = 58  # adjust to your font/width
        self._visible_lines = 3

    # ===== Public API =====

    def set_text(self, text: str):
        self.engine.set_text(text or "")
        self.current_text = text or ""
        self._render_line()

    def set_theme(self, theme):
        # allow theme colors to affect labels without touching global QSS
        self.setStyleSheet(
            f"""
            QLabel#lblLine {{ color: {theme.primary}; }}
            QLabel#lblTimer {{ color: {theme.secondary}; }}
            QLabel#lblWPM   {{ color: {theme.accent}; }}
            QLabel#lblAcc   {{ color: {theme.secondary}; }}
            """
        )

    def configure_session(
        self, time_limit=None, include_punct=True, include_numbers=True
    ):
        # reserved for future options
        pass

    def start_test(self, text: str | None = None):
        if text is not None:
            self.set_text(text)
        self.engine.reset()
        self._wpm_time.clear()
        self._wpm_vals.clear()
        self._active_seconds = 0.0
        self._caret_on = True
        self._render_line()
        self.timer.start()
        self._running = True
        self.setFocus()

    def pause_test(self):
        if self._running:
            self.timer.pause()

    def resume_test(self):
        if self._running:
            self.timer.resume()
            self._caret_on = True

    def finish_test(self):
        if self._running:
            self.timer.stop()
            self._running = False
        self.refresh_metrics()

        wpm = self.engine.wpm(self._active_seconds)
        acc = self.engine.accuracy() * 100.0
        snapshot = self.weak.snapshot()

        dlg = SessionSummary(
            wpm=wpm,
            acc=acc,
            secs=self._active_seconds,
            times=list(self._wpm_time),
            wpms=list(self._wpm_vals),
            parent=self,
        )
        dlg.exec()

        try:
            self.finished.emit(wpm, acc, self._active_seconds, snapshot)
        except Exception:
            pass

        self._render_line()

    # ===== Internals =====

    @Slot(float)
    def on_elapsed_changed(self, secs: float):
        self._active_seconds = secs
        self.lblTimer.setText(f"{secs:0.1f}s")

    def refresh_metrics(self):
        wpm = self.engine.wpm(self._active_seconds)
        acc = self.engine.accuracy() * 100.0
        self.lblWPM.setText(f"{wpm:0.1f} WPM")
        self.lblAcc.setText(f"{acc:0.1f}%")

        # buffer for summary graph
        self._wpm_time.append(self._active_seconds)
        self._wpm_vals.append(wpm)

    def _toggle_caret(self):
        self._caret_on = not self._caret_on
        if self._running:
            self._render_line()

    # ---- 3-line window rendering ----
    def _render_line(self):
        tgt = self.engine.target or ""
        typed = self.engine.typed or ""

        window_chars = self._approx_chars_per_line * self._visible_lines

        # compute the visible window by words near the caret
        start, end = self._compute_visible_window(tgt, typed, window_chars)
        display = tgt[start:end]
        typed_rel = max(0, len(typed) - start)
        typed_rel = min(typed_rel, len(display))

        parts = []
        # paint characters within window
        for idx, ch in enumerate(display):
            global_idx = start + idx
            if idx < typed_rel:
                if typed[global_idx] == tgt[global_idx]:
                    parts.append(f'<span style="color:#22c55e">{ch}</span>')
                else:
                    parts.append(f'<span style="color:#ef4444">{ch}</span>')
            else:
                parts.append(f'<span style="color:#6b7280">{ch}</span>')

        # caret
        caret_html = (
            '<span style="color:#eab308">|</span>'
            if self._caret_on
            else '<span style="color:transparent">|</span>'
        )
        caret_pos = typed_rel
        caret_pos = max(0, min(caret_pos, len(parts)))
        parts.insert(caret_pos, caret_html)

        self.lblLine.setText("".join(parts))

    def _compute_visible_window(
        self, tgt: str, typed: str, window_chars: int
    ) -> tuple[int, int]:
        """
        Return (start, end) indices of the slice of `tgt` to display
        so that ~3 lines are visible and the caret stays near the center.
        We respect word boundaries where possible.
        """
        n = len(tgt)
        caret = min(len(typed), n)

        # Aim caret in the middle of the window when possible
        half = window_chars // 2
        start = max(0, caret - half)
        end = min(n, start + window_chars)

        # expand end to next whitespace to avoid cutting a word at end
        while (
            end < n and not tgt[end - 1].isspace() and (end - start) < window_chars + 20
        ):
            end += 1

        # pull start back to previous whitespace
        while (
            start > 0
            and not tgt[start].isspace()
            and (end - start) <= window_chars + 20
        ):
            start -= 1

        # final clamp
        start = max(0, start)
        end = min(n, max(end, start + 1))
        return start, end

    # ===== Key handling =====

    def keyPressEvent(self, ev):
        if not self._running:
            return super().keyPressEvent(ev)

        nk = self._normalize_key(ev)
        if nk is None:
            return

        if nk == "<BACKSPACE>":
            self._backspace()
            return

        before = self.engine.stats.correct_chars
        self.engine.process_key(nk)
        correct_now = self.engine.stats.correct_chars > before
        self.weak.note(nk, correct_now)
        self._render_line()

    def _normalize_key(self, ev) -> str | None:
        if ev.isAutoRepeat():
            return None
        if ev.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return None

        key = ev.key()
        t = ev.text()

        if key == Qt.Key_Backspace:
            return "<BACKSPACE>"
        if key in (Qt.Key_Return, Qt.Key_Enter):
            return "\n"

        if t and (t >= " " or t == "\t"):
            return t
        return None

    def _backspace(self):
        if not self.engine.typed:
            return
        self.engine.typed = self.engine.typed[:-1]
        self._recount_stats()
        self._render_line()

    def _recount_stats(self):
        t, target = self.engine.typed, self.engine.target
        self.engine.stats.keystrokes = len(t)
        self.engine.stats.correct_chars = sum(
            1 for j, ch in enumerate(t) if j < len(target) and target[j] == ch
        )
        self.engine.stats.errors = (
            self.engine.stats.keystrokes - self.engine.stats.correct_chars
        )

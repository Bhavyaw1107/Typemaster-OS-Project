# ui/test_ui.py
from __future__ import annotations
from collections import deque

from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy

from services.typing_engine import TypingEngine
from services.weakkeys import WeakKeys
from core.chrono import RealtimeTimer
from ui.session_summary import SessionSummary


def _get(theme, name, default):
    return getattr(theme, name, default)


class TestUI(QWidget):
    finished = Signal(float, float, float, dict)  # wpm, acc%, secs, weakkeys_snapshot

    def __init__(self, parent=None):
        super().__init__(parent)

        # ===== Layout =====
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 30, 0, 30)
        root.setSpacing(28)

        # --- stats row ---
        stats = QHBoxLayout()
        stats.setSpacing(40)

        self.lblTimer = QLabel("0.0 s", self)
        self.lblTimer.setObjectName("lblTimer")
        self.lblTimer.setAlignment(Qt.AlignCenter)

        self.lblWPM = QLabel("0.0 WPM", self)
        self.lblWPM.setObjectName("lblWPM")
        self.lblWPM.setAlignment(Qt.AlignCenter)

        self.lblAcc = QLabel("0.0 %", self)
        self.lblAcc.setObjectName("lblAcc")
        self.lblAcc.setAlignment(Qt.AlignCenter)

        for lab in (self.lblTimer, self.lblWPM, self.lblAcc):
            stats.addWidget(lab)
        root.addLayout(stats)

        # --- typing line (HTML) ---
        self.lblLine = QLabel("", self)
        self.lblLine.setObjectName("lblLine")
        self.lblLine.setTextFormat(Qt.RichText)
        self.lblLine.setWordWrap(True)
        self.lblLine.setAlignment(Qt.AlignCenter)
        self.lblLine.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 🟢 Monkeytype-like width: wide but bounded so it reads well.
        # If you want even wider, bump max to 1200 or 1280.
        self.lblLine.setMinimumWidth(900)
        self.lblLine.setMaximumWidth(1100)
        self.lblLine.setMinimumHeight(140)
        root.addWidget(self.lblLine, stretch=1, alignment=Qt.AlignHCenter)

        # ===== Engines / timers =====
        self.engine = TypingEngine("")
        self.weak = WeakKeys()

        self.timer = RealtimeTimer(tick_ms=100, parent=self)
        self.timer.elapsedChanged.connect(self.on_elapsed_changed)

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
        self.current_text: str | None = None

        # Session config
        self._time_limit: int | None = None

        # Buffers for post-run graph
        self._wpm_time = deque(maxlen=3600)
        self._wpm_vals = deque(maxlen=3600)

        # ===== Viewport tuning =====
        # Target characters that fit in the visible area (approx).
        # Wider than before to mimic Monkeytype.
        self._approx_chars_per_line = 90
        self._visible_lines = 3

        # Jitter-free window: only shift when caret crosses margins.
        self._win_start = 0           # current window start (index in target)
        self._left_margin = 0.30      # keep caret inside 30%..70% band
        self._right_margin = 0.70

        # theme cache (updated by set_theme)
        self._colors = {
            "ok": "#22c55e",
            "err": "#ef4444",
            "mut": "#9aa1a9",
            "caret": "#eab308",
            "word_bg": "rgba(234,179,8,0.10)",
            "err_ul": "rgba(239,68,68,0.9)",
        }

        # Larger font for the whole typing line (Monkeytype vibe)
        # You can tweak size here if you want smaller/larger text.
        self.lblLine.setStyleSheet("font-size: 34px; line-height: 1.35;")

    # ===== Public API =====

    def set_text(self, text: str):
        self.engine.set_text(text or "")
        self.current_text = text or ""
        # reset viewport so we start at the beginning without a jump
        self._win_start = 0
        self._render_line()

    def set_theme(self, theme):
        self.setStyleSheet(
            f"""
            QLabel#lblLine {{ color: {_get(theme,'primary','#e5e7eb')}; }}
            QLabel#lblTimer {{ color: {_get(theme,'secondary','#9aa1a9')}; }}
            QLabel#lblWPM   {{ color: {_get(theme,'accent','#eab308')}; }}
            QLabel#lblAcc   {{ color: {_get(theme,'secondary','#9aa1a9')}; }}
            """
        )
        self._colors["ok"] = _get(theme, "correct", "#22c55e")
        self._colors["err"] = _get(theme, "error", "#ef4444")
        self._colors["mut"] = _get(theme, "text_muted", _get(theme, "secondary", "#9aa1a9"))
        self._colors["caret"] = _get(theme, "caret", _get(theme, "accent", "#eab308"))
        acc = _get(theme, "accent", "#eab308")
        self._colors["word_bg"] = self._hex_to_rgba(acc, 0.10)
        self._colors["err_ul"] = self._hex_to_rgba(self._colors["err"], 0.9)
        self._render_line()

    def configure_session(self, time_limit=None):
        try:
            self._time_limit = int(time_limit) if time_limit else None
        except Exception:
            self._time_limit = None

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

        try:
            dlg = SessionSummary(
                wpm=wpm,
                acc=acc,
                secs=self._active_seconds,
                times=list(self._wpm_time),
                wpms=list(self._wpm_vals),
                parent=self,
            )
            dlg.exec()
        except Exception:
            pass

        try:
            self.finished.emit(wpm, acc, self._active_seconds, snapshot)
        except Exception:
            pass

        self._render_line()

    # ===== Internals =====

    @Slot(float)
    def on_elapsed_changed(self, secs: float):
        self._active_seconds = secs
        self.lblTimer.setText(f"{secs:0.1f} s")

        if self._running and self._time_limit and secs >= float(self._time_limit):
            self.finish_test()
            return

    def refresh_metrics(self):
        wpm = self.engine.wpm(self._active_seconds)
        acc = self.engine.accuracy() * 100.0
        self.lblWPM.setText(f"{wpm:0.1f} WPM")
        self.lblAcc.setText(f"{acc:0.1f} %")
        self._wpm_time.append(self._active_seconds)
        self._wpm_vals.append(wpm)

    def _toggle_caret(self):
        self._caret_on = not self._caret_on
        if self._running:
            self._render_line()

    # ---- Render with jitter-free viewport ----
    def _render_line(self):
        tgt = self.engine.target or ""
        typed = self.engine.typed or ""

        window_chars = self._approx_chars_per_line * self._visible_lines
        caret = min(len(typed), len(tgt))

        # Keep a stable window: only move when caret leaves a central band.
        left_band = self._win_start + int(window_chars * self._left_margin)
        right_band = self._win_start + int(window_chars * self._right_margin)

        if caret < left_band or caret > right_band:
            # Re-center caret into the band; snap start to a word boundary.
            desired_center = self._win_start + window_chars // 2
            # shift so caret heads to middle
            shift = caret - desired_center
            new_start = max(0, self._win_start + shift)

            # Respect word boundary backwards a bit
            new_start = self._snap_to_prev_space(tgt, new_start, limit=40)
            self._win_start = new_start

        start = self._win_start
        end = min(len(tgt), start + window_chars)
        display = tgt[start:end]

        typed_rel = max(0, len(typed) - start)
        typed_rel = min(typed_rel, len(display))

        col_ok = self._colors["ok"]
        col_err = self._colors["err"]
        col_mut = self._colors["mut"]
        col_caret = self._colors["caret"]
        word_bg = self._colors["word_bg"]
        err_ul = self._colors["err_ul"]

        # current word highlight bounds
        caret_global = caret
        w_start = self._find_word_start(tgt, caret_global)
        w_end = self._find_word_end(tgt, caret_global)
        w_start_rel = max(0, w_start - start)
        w_end_rel = max(0, min(w_end - start, len(display)))

        parts: list[str] = []

        def span(txt: str, color: str | None = None, underline: bool = False, bg: str | None = None):
            style_bits = []
            if color:
                style_bits.append(f"color:{color}")
            if underline:
                style_bits.append(f"border-bottom:2px solid {err_ul}")
            if bg:
                style_bits.append(f"background:{bg}; border-radius:6px; padding:2px 2px;")
            style = ";".join(style_bits)
            return f'<span style="{style}">{txt}</span>'

        # build spans
        for idx, ch in enumerate(display):
            global_idx = start + idx
            highlight_bg = None
            if w_start_rel <= idx < w_end_rel and idx >= typed_rel:
                highlight_bg = word_bg

            if idx < typed_rel:
                if global_idx < len(tgt) and typed[global_idx] == tgt[global_idx]:
                    parts.append(span(ch, col_ok))
                else:
                    parts.append(span(ch, col_err, underline=True))
            else:
                parts.append(span(ch, col_mut, bg=highlight_bg))

        # caret
        caret_html = (f'<span style="color:{col_caret}">|</span>'
                      if self._caret_on else '<span style="color:transparent">|</span>')
        parts.insert(max(0, min(typed_rel, len(parts))), caret_html)

        self.lblLine.setText("".join(parts))

        # finish when text consumed
        if self._running and len(self.engine.typed) >= len(self.engine.target):
            self.finish_test()

    # ===== helpers =====
    def _find_word_start(self, text: str, pos: int) -> int:
        i = max(0, min(pos, len(text)))
        while i > 0 and not text[i - 1].isspace():
            i -= 1
        return i

    def _find_word_end(self, text: str, pos: int) -> int:
        i = max(0, min(pos, len(text)))
        n = len(text)
        while i < n and not text[i].isspace():
            i += 1
        return i

    def _snap_to_prev_space(self, text: str, start: int, limit: int = 40) -> int:
        """Walk back up to `limit` chars to land on a whitespace; keeps window stable."""
        i = max(0, min(start, len(text)))
        walked = 0
        while i > 0 and walked < limit and not text[i - 1].isspace():
            i -= 1
            walked += 1
        return i

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

        if len(self.engine.typed) >= len(self.engine.target):
            self.finish_test()

    def _normalize_key(self, ev) -> str | None:
        # allow OS key auto-repeat; only ignore when modifier combos are active
        if ev.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return None

        key = ev.key()
        t = ev.text()

        if key == Qt.Key_Backspace:
            return "<BACKSPACE>"          # backspace will also auto-repeat when held
        if key in (Qt.Key_Return, Qt.Key_Enter):
            return "\n"

        if t and (t >= " " or t == "\t"): # printable characters (space and above, plus tab)
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

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return "rgba(255,255,255,0.10)"
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return f"rgba({r},{g},{b},{max(0.0, min(alpha, 1.0))})"

# ui/widgets/typing_area.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QFont, QColor, QPen
from PySide6.QtCore import Qt, QTimer, QRectF


def _pick(theme, attr, default):
    return getattr(theme, attr, default)


class TypingArea(QWidget):
    """
    High-performance renderer for "words mode".
    Parent provides:
      - get_state(): object with .target_text, .position, .keystrokes (list with .correct)
      - get_theme(): theme object (at least background/primary/secondary/accent)
    """

    def __init__(self, get_state_fn, get_theme_fn, parent=None):
        super().__init__(parent)
        self.get_state = get_state_fn
        self.get_theme = get_theme_fn
        self.setFocusPolicy(Qt.StrongFocus)

        # Visuals tuned for readability like monkeytype
        self._font = QFont("Inter, Segoe UI, Roboto, Arial", 28)
        self._line_wrap_px = 1000  # target line width for wrapping
        self._line_height = 52

        # Caret blink
        self._blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle_blink)
        self._timer.start(500)

        # padding
        self._pad_x = 32
        self._pad_y = 32

    def _toggle_blink(self):
        self._blink = not self._blink
        self.update()

    def paintEvent(self, e):
        s = self.get_state()
        theme = self.get_theme()

        # Resolve theme colors with fallbacks
        bg = _pick(theme, "background", "#0f1115")
        surface = _pick(theme, "surface", bg)  # fallback to background
        ok = _pick(theme, "correct", "#22c55e")
        err = _pick(theme, "error", "#ef4444")
        caret = _pick(theme, "caret", _pick(theme, "accent", "#eab308"))
        muted = _pick(theme, "text_muted", _pick(theme, "secondary", "#6b7280"))

        p = QPainter(self)
        p.fillRect(self.rect(), QColor(surface))
        p.setFont(self._font)
        fm = p.fontMetrics()

        # center panel look
        panel_rect = self.rect().adjusted(self._pad_x, self._pad_y, -self._pad_x, -self._pad_y)
        # limit width for readability
        max_w = min(self._line_wrap_px, panel_rect.width())
        left = panel_rect.center().x() - max_w / 2
        x = left
        y = panel_rect.top() + self._line_height

        wchar = fm.horizontalAdvance("M")

        # quick helpers
        def draw_char(ch_i: int, ch: str):
            nonlocal x, y
            if ch == "\n" or x + wchar > left + max_w:
                x = left
                y += self._line_height

            # color by state
            if ch_i < len(s.keystrokes):
                is_ok = getattr(s.keystrokes[ch_i], "correct", False)
                p.setPen(QColor(ok if is_ok else err))
            elif ch_i == s.position and self._blink:
                p.setPen(QColor(caret))
            elif ch_i < s.position:
                p.setPen(QColor(ok))
            else:
                p.setPen(QColor(muted))

            p.drawText(
                QRectF(x, y - self._line_height + 6, wchar + 2, self._line_height),
                Qt.AlignLeft | Qt.AlignVCenter,
                ch if ch != "\n" else " ",
            )

            # underline for wrong chars
            if ch_i < len(s.keystrokes) and not getattr(s.keystrokes[ch_i], "correct", False):
                pen = QPen(QColor(err))
                pen.setWidth(2)
                p.setPen(pen)
                p.drawLine(x, y - 6, x + wchar - 6, y - 6)

            x += wchar

        # draw text
        for i, ch in enumerate(getattr(s, "target_text", "")):
            draw_char(i, ch)

        # caret after last char
        if getattr(s, "position", 0) >= len(getattr(s, "target_text", "")) and self._blink:
            p.setPen(QColor(caret))
            p.drawText(x, y, "|")

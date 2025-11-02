from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QFont, QColor, QPen
from PySide6.QtCore import Qt, QTimer, QRectF

class TypingArea(QWidget):
    """
    High-performance renderer for "words mode":
    - Fixed line width for comfortable reading (~70–80 chars).
    - Per-char coloring:
        pending -> muted grey
        correct -> theme.correct
        wrong   -> theme.error
    - Blinking caret at current index.
    Parent handles all key logic & state; this class only paints `state.target_text`,
    using `state.position` and `state.keystrokes`.
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

        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.surface))
        p.setFont(self._font)
        fm = p.fontMetrics()

        # center panel look
        panel_rect = self.rect().adjusted(self._pad_x, self._pad_y, -self._pad_x, -self._pad_y)
        # limit width for readability
        max_w = min(self._line_wrap_px, panel_rect.width())
        left = panel_rect.center().x() - max_w/2
        x = left
        y = panel_rect.top() + self._line_height

        wchar = fm.horizontalAdvance("M")

        # quick helpers
        def draw_char(ch_i: int, ch: str):
            nonlocal x, y
            if ch == '\n' or x + wchar > left + max_w:
                x = left
                y += self._line_height

            # color by state
            if ch_i < len(s.keystrokes):
                ok = s.keystrokes[ch_i].correct
                p.setPen(QColor(theme.correct if ok else theme.error))
            elif ch_i == s.position and self._blink:
                p.setPen(QColor(theme.caret))
            elif ch_i < s.position:
                p.setPen(QColor(theme.correct))
            else:
                p.setPen(QColor(theme.text_muted))

            p.drawText(QRectF(x, y - self._line_height + 6, wchar + 2, self._line_height),
                       Qt.AlignLeft | Qt.AlignVCenter, ch if ch != '\n' else " ")

            # underline for wrong chars
            if ch_i < len(s.keystrokes) and not s.keystrokes[ch_i].correct:
                pen = QPen(QColor(theme.error)); pen.setWidth(2)
                p.setPen(pen)
                p.drawLine(x, y - 6, x + wchar - 6, y - 6)

            x += wchar

        # draw text
        for i, ch in enumerate(s.target_text):
            draw_char(i, ch)

        # caret after last char
        if s.position >= len(s.target_text) and self._blink:
            p.setPen(QColor(theme.caret))
            p.drawText(x, y, "|")

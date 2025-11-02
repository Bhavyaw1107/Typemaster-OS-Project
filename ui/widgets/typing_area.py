from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QFont, QColor, QPen
from PySide6.QtCore import Qt, QTimer, QRect

class TypingArea(QWidget):
    """
    Visual-only widget:
    - Shows target text with per-character colors (correct/error/pending).
    - Blinking caret at current position.
    Parent (TestUI) handles key input and state; this just paints.
    """
    def __init__(self, get_state_fn, get_theme_fn, parent=None):
        super().__init__(parent)
        self.get_state = get_state_fn
        self.get_theme = get_theme_fn
        self.setFocusPolicy(Qt.StrongFocus)
        self._font = QFont("Inter, Segoe UI, Roboto, Arial", 24)
        self._line_wrap = 900  # px
        self._blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle_blink)
        self._timer.start(550)

    def _toggle_blink(self):
        self._blink = not self._blink
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        theme = self.get_theme()
        st = self.get_state()

        painter.fillRect(self.rect(), QColor(theme.surface))
        painter.setFont(self._font)

        x, y = 24, 48
        lh = 44
        fm = painter.fontMetrics()
        wchar = fm.horizontalAdvance("M")
        h = fm.height()
        pos = st.position

        def draw_char(ch, idx, rect):
            if idx < len(st.keystrokes):
                ok = st.keystrokes[idx].correct
                painter.setPen(QColor(theme.correct if ok else theme.error))
            elif idx == pos and self._blink:
                painter.setPen(QColor(theme.caret))
            elif idx < pos:
                painter.setPen(QColor(theme.correct))
            else:
                painter.setPen(QColor(theme.text_muted))

            painter.drawText(rect.left(), rect.top(), rect.width(), rect.height(),
                             Qt.AlignLeft | Qt.AlignVCenter, ch)

            if idx < len(st.keystrokes) and not st.keystrokes[idx].correct:
                pen = QPen(QColor(theme.error))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawLine(rect.left(), rect.bottom()-6, rect.left()+12, rect.bottom()-6)

        for i, ch in enumerate(st.target_text):
            if ch == '\n' or x + wchar > self._line_wrap:
                x = 24
                y += lh
            rect = QRect(x, y-h, wchar+2, lh)
            draw_char(ch, i, rect)
            x += wchar

        if pos >= len(st.target_text) and self._blink:
            painter.setPen(QColor(theme.caret))
            painter.drawText(x, y, "|")

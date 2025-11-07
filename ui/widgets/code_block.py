from PySide6.QtWidgets import QPlainTextEdit, QTextEdit
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor, QPainter
from PySide6.QtCore import Qt, QRect, QTimer, Signal


class CodeBlock(QPlainTextEdit):
    """Monospace code display with color feedback and visible caret."""

    key_pressed = Signal(str)

    def __init__(self, parent=None, font_size: int = 16):
        super().__init__(parent)

        self.setReadOnly(False)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFocusPolicy(Qt.StrongFocus)

        font = QFont("Courier New", font_size)
        if not font.exactMatch():
            font = QFont("Consolas", font_size)
        if not font.exactMatch():
            font = QFont("Monaco", font_size)
        font.setFixedPitch(True)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        metrics = self.fontMetrics()
        self.setTabStopDistance(4 * metrics.horizontalAdvance(" "))

        self._caret_pos = 0
        self._caret_visible = True
        self._typed = ""
        self._target = ""

        self._color_correct = QColor("#22c55e")
        self._color_error = QColor("#ef4444")
        self._color_untyped = QColor("#9aa1a9")
        self._caret_color = QColor("#eab308")

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0f1115;
                color: #9aa1a9;
                border: none;
                padding: 15px;
            }
        """)

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink_caret)
        self._blink_timer.start(500)
        self._blink_state = True

    def _blink_caret(self):
        if self._caret_visible:
            self._blink_state = not self._blink_state
            self.viewport().update()

    def set_code(self, code: str):
        self.setPlainText(code)
        self._target = code
        self._typed = ""
        self._caret_pos = 0
        self._caret_visible = True
        self._blink_state = True
        self._apply_colors()
        self.viewport().update()

    def set_typing_state(self, typed: str, target: str):
        """Update typing state for color feedback."""
        self._typed = typed
        self._target = target
        self._caret_pos = len(typed)
        self._caret_visible = True
        self._blink_state = True
        self._apply_colors()
        self.viewport().update()

    def _apply_colors(self):
        """Color characters based on correctness - NO UNDERLINES."""
        selections = []
        typed_len = len(self._typed)
        target_len = len(self._target)

        for i in range(target_len):
            cursor = QTextCursor(self.document())
            cursor.setPosition(i)
            cursor.setPosition(i + 1, QTextCursor.KeepAnchor)

            fmt = QTextCharFormat()
            fmt.setUnderlineStyle(QTextCharFormat.NoUnderline)

            if i < typed_len:
                if self._typed[i] == self._target[i]:
                    fmt.setForeground(self._color_correct)
                else:
                    fmt.setForeground(self._color_error)
            else:
                fmt.setForeground(self._color_untyped)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = fmt
            selections.append(selection)

        self.setExtraSelections(selections)

    def set_caret(self, pos: int, visible: bool = True):
        self._caret_pos = max(0, min(pos, len(self.toPlainText())))
        self._caret_visible = visible
        self._blink_state = True

        cursor = QTextCursor(self.document())
        cursor.setPosition(self._caret_pos)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.viewport().update()

    def clear_caret(self):
        self._caret_visible = False
        self.viewport().update()

    def set_theme_colors(self, correct: str, error: str, untyped: str, caret: str):
        self._color_correct = QColor(correct)
        self._color_error = QColor(error)
        self._color_untyped = QColor(untyped)
        self._caret_color = QColor(caret)
        self._apply_colors()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._caret_visible and self._blink_state:
            painter = QPainter(self.viewport())
            cursor = QTextCursor(self.document())
            cursor.setPosition(self._caret_pos)
            rect = self.cursorRect(cursor)
            caret_rect = QRect(rect.x(), rect.y(), 3, rect.height())
            painter.fillRect(caret_rect, self._caret_color)
            painter.end()

    def keyPressEvent(self, event):
        event.ignore()
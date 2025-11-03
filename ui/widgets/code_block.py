# ui/widgets/code_block.py
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor, QPainter
from PySide6.QtCore import Qt, QRect, QTimer

class CodeBlock(QPlainTextEdit):
    """Monospace code display with color feedback and visible caret."""

    def __init__(self, parent=None, font_size: int = 16):
        super().__init__(parent)
        self.setReadOnly(True)
        
        # Set monospace font
        font = QFont("Courier New", font_size)
        if not font.exactMatch():
            font = QFont("Consolas", font_size)
        if not font.exactMatch():
            font = QFont("Monaco", font_size)
        font.setFixedPitch(True)
        self.setFont(font)

        # Critical: No word wrap
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Tab = 4 spaces
        metrics = self.fontMetrics()
        self.setTabStopDistance(4 * metrics.horizontalAdvance(" "))

        # State
        self._caret_pos = 0
        self._caret_visible = True
        self._typed = ""
        self._target = ""
        
        # Colors
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
        
        # Blink timer
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink_caret)
        self._blink_timer.start(500)
        self._blink_state = True

    def _blink_caret(self):
        """Toggle caret visibility for blinking effect."""
        if self._caret_visible:
            self._blink_state = not self._blink_state
            self.viewport().update()

    def set_code(self, code: str):
        """Set code preserving exact formatting including indentation."""
        # Don't modify the code - preserve tabs, spaces, newlines exactly
        self.setPlainText(code)
        self._target = code
        self._typed = ""
        self._caret_pos = 0
        self._blink_state = True
        self._apply_colors()

    def set_typing_state(self, typed: str, target: str):
        """Update typing state for color feedback."""
        self._typed = typed
        self._target = target
        self._caret_pos = len(typed)
        self._blink_state = True
        self._apply_colors()

    def _apply_colors(self):
        """Color characters based on correctness."""
        selections = []
        typed_len = len(self._typed)
        target_len = len(self._target)
        
        for i in range(target_len):
            cursor = QTextCursor(self.document())
            cursor.setPosition(i)
            cursor.setPosition(i + 1, QTextCursor.KeepAnchor)
            
            fmt = QTextCharFormat()
            
            if i < typed_len:
                if i < len(self._target) and self._typed[i] == self._target[i]:
                    fmt.setForeground(self._color_correct)
                else:
                    fmt.setForeground(self._color_error)
                    fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                    fmt.setUnderlineColor(self._color_error)
            else:
                fmt.setForeground(self._color_untyped)
            
            selection = QPlainTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = fmt
            selections.append(selection)
        
        self.setExtraSelections(selections)

    def set_caret(self, pos: int, visible: bool = True):
        """Set caret position and visibility."""
        self._caret_pos = max(0, min(pos, len(self.toPlainText())))
        self._caret_visible = visible
        self._blink_state = True
        
        cursor = QTextCursor(self.document())
        cursor.setPosition(self._caret_pos)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.viewport().update()

    def clear_caret(self):
        """Hide caret."""
        self._caret_visible = False
        self.viewport().update()

    def set_theme_colors(self, correct: str, error: str, untyped: str, caret: str):
        """Update colors from theme."""
        self._color_correct = QColor(correct)
        self._color_error = QColor(error)
        self._color_untyped = QColor(untyped)
        self._caret_color = QColor(caret)
        self._apply_colors()

    def paintEvent(self, event):
        """Draw text and caret."""
        super().paintEvent(event)
        
        if self._caret_visible and self._blink_state:
            painter = QPainter(self.viewport())
            cursor = QTextCursor(self.document())
            cursor.setPosition(self._caret_pos)
            rect = self.cursorRect(cursor)
            
            # Draw thick yellow vertical line
            painter.fillRect(rect.x(), rect.y(), 3, rect.height(), self._caret_color)
            painter.end()
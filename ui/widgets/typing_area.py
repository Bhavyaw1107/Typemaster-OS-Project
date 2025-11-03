# ui/widgets/typing_area.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QFont, QColor, QPen, QPaintEvent
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QFontMetricsF

def _pick(theme, attr, default):
    return getattr(theme, attr, default)


class TypingArea(QWidget):
    """
    Word-based renderer that avoids jumps:
      - Lays out by WORDS using exact font metrics
      - Maps characters back to word positions (so each word is atomic)
      - Smoothly animates vertical offset to center the active word's line
    API unchanged: __init__(get_state_fn, get_theme_fn, parent=None)
    get_state() must provide: .target_text (str), .position (int), .keystrokes (list-like with .correct)
    """

    def __init__(self, get_state_fn, get_theme_fn, parent=None):
        super().__init__(parent)
        self.get_state = get_state_fn
        self.get_theme = get_theme_fn
        self.setFocusPolicy(Qt.StrongFocus)

        # Visuals
        self._font = QFont("Inter, Segoe UI, Roboto, Arial", 28)
        self._line_wrap_px = 1000
        self._line_height = 52
        self._pad_x = 32
        self._pad_y = 32

        # blink + animation timers
        self._blink = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.start(500)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_timer.start()

        # layout caches
        self._word_positions: list[QPointF] = []  # per-word top-left of word box
        self._word_widths: list[float] = []
        self._word_char_ranges: list[tuple[int,int]] = []  # (char_start, char_end_exclusive)
        self._char_to_word: list[int] = []  # index->word index
        self._lines: list[list[int]] = []  # line -> list of word indices

        # animation offsets
        self._offset_y = 0.0
        self._target_offset_y = 0.0

        # last knowns
        self._last_text = None
        self._last_wrap = None
        self._last_pos = None

    # ---------- blink ----------
    def _toggle_blink(self):
        self._blink = not self._blink
        self.update()

    # ---------- resize / reflow ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()
        s = self.get_state()
        self._update_target_offset(getattr(s, "position", 0))

    def _split_words_with_indices(self, text: str):
        """
        Split text into words but preserve their exact spans (including spaces/newlines).
        We'll treat whitespace between words as part of the following word's prefix when placing.
        Returns list of tuples: (word_text, start_index, end_index)
        """
        words = []
        i = 0
        n = len(text)
        while i < n:
            # skip leading spaces/newlines and keep them attached to next non-space chunk
            ws_start = i
            while i < n and text[i].isspace():
                i += 1
            ws = text[ws_start:i]  # could be empty
            # now collect non-space chunk
            chunk_start = i
            while i < n and not text[i].isspace():
                i += 1
            chunk = text[chunk_start:i]
            if chunk == "" and ws == "":
                break
            # If chunk is empty but there were spaces (like trailing spaces or newlines),
            # represent them as a word of just whitespace so they get rendered (space glyphs)
            if chunk == "" and ws != "":
                words.append((ws, ws_start, i))
            else:
                # attach preceding whitespace to this chunk (so it moves with the word)
                full = ws + chunk
                words.append((full, ws_start, i))
        return words

    def _reflow(self):
        """Compute positions for words (not per char) using exact font metrics."""
        s = self.get_state()
        text = getattr(s, "target_text", "") or ""
        panel_rect = self.rect().adjusted(self._pad_x, self._pad_y, -self._pad_x, -self._pad_y)
        wrap_w = min(self._line_wrap_px, max(10, panel_rect.width()))

        # small change detection
        if text == self._last_text and wrap_w == self._last_wrap:
            return
        self._last_text = text
        self._last_wrap = wrap_w

        fm = QFontMetricsF(self._font)
        self._line_height = max(self._line_height, fm.height(), 28)

        # split into logical "words" preserving spaces as prefix
        word_entries = self._split_words_with_indices(text)

        self._word_positions = []
        self._word_widths = []
        self._word_char_ranges = []
        self._char_to_word = []
        self._lines = []

        left = panel_rect.center().x() - wrap_w / 2
        cur_x = left
        cur_y_top = panel_rect.top()
        cur_line = []
        char_index = 0

        for w_idx, (word_text, start_idx, end_idx) in enumerate(word_entries):
            w_width = fm.horizontalAdvance(word_text if word_text != "\n" else " ")
            # If the word contains newline(s), split by newline boundaries for layout
            if "\n" in word_text:
                parts = word_text.split("\n")
                # place pre-newline parts
                for pi, part in enumerate(parts):
                    if part == "" and pi == len(parts)-1:
                        # trailing newline -> force line break
                        if cur_line:
                            self._lines.append(cur_line)
                        cur_line = []
                        cur_x = left
                        cur_y_top += self._line_height
                        continue
                    part_text = part
                    part_w = fm.horizontalAdvance(part_text if part_text != "" else " ")
                    # wrap if needed
                    if cur_line and (cur_x + part_w > left + wrap_w):
                        self._lines.append(cur_line)
                        cur_line = []
                        cur_x = left
                        cur_y_top += self._line_height
                    # store word (the "part") as a unit
                    self._word_positions.append(QPointF(cur_x, cur_y_top))
                    self._word_widths.append(part_w)
                    # compute char range for the part: we must keep char indices consistent
                    part_len = len(part_text)
                    self._word_char_ranges.append((char_index, char_index + part_len))
                    for _ in range(part_len):
                        self._char_to_word.append(len(self._word_positions)-1)
                    char_index += part_len
                    cur_x += part_w
                    cur_line.append(len(self._word_positions)-1)
                    # newline -> wrap to next line
                    if pi < len(parts)-1:
                        if cur_line:
                            self._lines.append(cur_line)
                        cur_line = []
                        cur_x = left
                        cur_y_top += self._line_height
                continue  # next word entry

            # Normal single "word" (may include leading spaces)
            # wrap if needed
            if cur_line and (cur_x + w_width > left + wrap_w):
                self._lines.append(cur_line)
                cur_line = []
                cur_x = left
                cur_y_top += self._line_height

            self._word_positions.append(QPointF(cur_x, cur_y_top))
            self._word_widths.append(w_width)
            word_char_len = end_idx - start_idx
            self._word_char_ranges.append((char_index, char_index + word_char_len))
            for _ in range(word_char_len):
                self._char_to_word.append(len(self._word_positions)-1)
            char_index += word_char_len
            cur_x += w_width
            cur_line.append(len(self._word_positions)-1)

        if cur_line:
            self._lines.append(cur_line)

    # ---------- animation ----------
    def _anim_tick(self):
        if abs(self._offset_y - self._target_offset_y) < 0.25:
            self._offset_y = self._target_offset_y
        else:
            self._offset_y += (self._target_offset_y - self._offset_y) * 0.22
        # bounding to avoid exposing huge empty areas
        if self._lines and self._word_positions:
            last_word_idx = self._lines[-1][-1]
            last_y = self._word_positions[last_word_idx].y()
            bottom_limit = (self.height() / 2.0) - (last_y + self._line_height / 2.0)
            self._offset_y = max(bottom_limit - 40, min(40, self._offset_y))
        self.update()

    def _update_target_offset(self, char_index: int):
        """Center the line of the word which contains char_index."""
        if not self._lines or not self._word_positions or char_index < 0:
            self._target_offset_y = 0.0
            return
        # handle char_index beyond text (center last line)
        if char_index >= len(self._char_to_word):
            line_idx = len(self._lines) - 1
        else:
            word_idx = self._char_to_word[char_index] if char_index < len(self._char_to_word) else 0
            # find which line contains this word
            line_idx = 0
            for li, line in enumerate(self._lines):
                if word_idx in line:
                    line_idx = li
                    break

        panel_rect = self.rect().adjusted(self._pad_x, self._pad_y, -self._pad_x, -self._pad_y)
        target_line_top = panel_rect.top() + line_idx * self._line_height
        center_y = self.height() / 2.0
        self._target_offset_y = center_y - (target_line_top + self._line_height / 2.0)

    # ---------- painting ----------
    def paintEvent(self, e: QPaintEvent):
        s = self.get_state()
        theme = self.get_theme()
        bg = _pick(theme, "background", "#0f1115")
        surface = _pick(theme, "surface", bg)
        ok = _pick(theme, "correct", "#22c55e")
        err = _pick(theme, "error", "#ef4444")
        caret = _pick(theme, "caret", _pick(theme, "accent", "#eab308"))
        muted = _pick(theme, "text_muted", _pick(theme, "secondary", "#6b7280"))

        # ensure layout up-to-date
        self._reflow()

        pos = getattr(s, "position", 0)
        if pos != self._last_pos:
            self._last_pos = pos
            self._update_target_offset(pos)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(surface))
        p.setFont(self._font)
        fm = QFontMetricsF(self._font)
        ascent = fm.ascent()

        panel_rect = self.rect().adjusted(self._pad_x, self._pad_y, -self._pad_x, -self._pad_y)

        text = getattr(s, "target_text", "") or ""

        # draw words (each word draws all its characters together)
        for w_idx, pos_pt in enumerate(self._word_positions):
            x = pos_pt.x()
            y_top = pos_pt.y() + self._offset_y
            # cull
            if y_top + self._line_height < -200 or y_top > self.height() + 200:
                continue
            word_text = ""
            # reconstruct substring for this word (using char ranges)
            cstart, cend = self._word_char_ranges[w_idx]
            if cstart < len(text):
                word_text = text[cstart:min(cend, len(text))]
            else:
                word_text = ""

            # draw characters in the word, coloring by each char's keystroke info
            char_x = x
            for ci in range(cstart, cend):
                ch = text[ci] if ci < len(text) else " "
                ch_w = fm.horizontalAdvance(ch if ch != "\n" else " ")
                # choose color:
                if ci < len(getattr(s, "keystrokes", [])):
                    is_ok = getattr(s.keystrokes[ci], "correct", False)
                    pen_color = QColor(ok if is_ok else err)
                elif ci == pos and self._blink:
                    pen_color = QColor(caret)
                elif ci < pos:
                    pen_color = QColor(ok)
                else:
                    pen_color = QColor(muted)

                p.setPen(pen_color)
                baseline_y = y_top + ascent + (self._line_height - fm.height()) / 2.0
                p.drawText(QPointF(char_x, baseline_y), ch if ch != "\n" else " ")
                # underline wrong char
                if ci < len(getattr(s, "keystrokes", [])) and not getattr(s.keystrokes[ci], "correct", False):
                    pen = QPen(QColor(err))
                    pen.setWidth(2)
                    p.setPen(pen)
                    uy = baseline_y + 6
                    p.drawLine(char_x, uy, char_x + ch_w - 2, uy)
                char_x += ch_w

        # caret after last char
        text_len = len(getattr(s, "target_text", "") or "")
        if pos >= text_len and self._blink:
            # find location after last char
            if text_len > 0:
                last_char = text_len - 1
                last_word_idx = self._char_to_word[last_char]
                last_word_pos = self._word_positions[last_word_idx]
                # compute x by summing widths inside last word up to last char
                fm_local = fm
                cstart, cend = self._word_char_ranges[last_word_idx]
                caret_x = last_word_pos.x()
                for ci in range(cstart, text_len):
                    caret_x += fm_local.horizontalAdvance(text[ci] if text[ci] != "\n" else " ")
                caret_y_top = last_word_pos.y() + self._offset_y
            else:
                # empty text -> caret at left start
                wrap_w = min(self._line_wrap_px, max(10, panel_rect.width()))
                left = panel_rect.center().x() - wrap_w / 2
                caret_x = left
                caret_y_top = panel_rect.top() + self._offset_y

            p.setPen(QColor(caret))
            baseline = caret_y_top + ascent + (self._line_height - fm.height()) / 2.0
            p.drawText(QPointF(caret_x, baseline), "|")

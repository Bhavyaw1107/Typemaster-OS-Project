# services/typing_engine.py
from dataclasses import dataclass

@dataclass
class TypingStats:
    keystrokes: int = 0
    correct_chars: int = 0
    errors: int = 0

class TypingEngine:
    def __init__(self, target_text: str = ""):
        self.set_text(target_text)
        self.stats = TypingStats()

    def set_text(self, text: str):
        self.target = text or ""
        self.typed = ""

    def reset(self):
        self.typed = ""
        self.stats = TypingStats()

    def process_key(self, ch: str):
        if not ch:
            return
        self.stats.keystrokes += 1
        if len(self.typed) < len(self.target) and ch == self.target[len(self.typed)]:
            self.stats.correct_chars += 1
        else:
            self.stats.errors += 1
        self.typed += ch

    def accuracy(self) -> float:
        k = max(1, self.stats.keystrokes)
        return max(0.0, min(1.0, self.stats.correct_chars / k))

    def wpm(self, active_seconds: float) -> float:
        # WPM = (correct_chars / 5) / (active_time_minutes)
        s = max(1e-6, active_seconds)
        return (self.stats.correct_chars / 5.0) / (s / 60.0)

# services/weakkeys.py
from collections import Counter

class WeakKeys:
    def __init__(self):
        self.counts = Counter()

    def note(self, ch: str, correct: bool):
        if not ch:
            return
        key = ch.lower()
        # increment “weakness” on mistakes more than on correct
        self.counts[key] += 2 if not correct else 0.5

    def snapshot(self) -> dict:
        return dict(self.counts)

from dataclasses import dataclass, field
from typing import Dict, List
import time

@dataclass
class Keystroke:
    t: float
    key: str
    correct: bool

@dataclass
class TestState:
    target_text: str = ""
    position: int = 0
    started_at: float = 0.0
    ended_at: float = 0.0
    keystrokes: List[Keystroke] = field(default_factory=list)
    weak_keys: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def reset(self, text: str):
        self.target_text = text
        self.position = 0
        self.started_at = 0.0
        self.ended_at = 0.0
        self.keystrokes.clear()

    @property
    def is_running(self) -> bool:
        return self.started_at > 0.0 and self.ended_at == 0.0

    def start(self):
        if self.started_at == 0.0:
            self.started_at = time.time()

    def stop(self):
        if self.ended_at == 0.0:
            self.ended_at = time.time()

    def duration(self) -> float:
        end = self.ended_at or time.time()
        return max(0.001, end - self.started_at) if self.started_at else 0.0

    def mark_key(self, key: str, correct: bool):
        self.keystrokes.append(Keystroke(time.time(), key, correct))
        bucket = self.weak_keys.setdefault(key, {"hit": 0, "miss": 0})
        bucket["hit" if correct else "miss"] += 1

    def accuracy(self) -> float:
        if not self.keystrokes:
            return 100.0
        hits = sum(1 for k in self.keystrokes if k.correct)
        return 100.0 * hits / len(self.keystrokes)

    def wpm(self) -> float:
        dur = self.duration()
        if dur <= 0:
            return 0.0
        correct_chars = sum(1 for k in self.keystrokes if k.correct)
        return (correct_chars / 5.0) / (dur / 60.0)

    def weak_keys_ranked(self):
        result = []
        for k, v in self.weak_keys.items():
            total = v["hit"] + v["miss"]
            if total == 0:
                continue
            miss_rate = v["miss"] / total
            result.append((k, miss_rate, v["hit"], v["miss"]))
        return sorted(result, key=lambda x: (-x[1], -(x[2]+x[3])))

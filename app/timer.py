from PySide6.QtCore import QElapsedTimer

class HighResTimer:
    def __init__(self):
        self.t = QElapsedTimer()
    def start(self):
        self.t.start()
    def elapsed_sec(self) -> float:
        return max(0.0, self.t.elapsed() / 1000.0)

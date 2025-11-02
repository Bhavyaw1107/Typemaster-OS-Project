# core/threads.py
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

class TextLoadWorkerSignals(QObject):
    loaded = Signal(str)
    failed = Signal(str)

class TextLoadWorker(QRunnable):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.signals = TextLoadWorkerSignals()

    def run(self):
        try:
            with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                data = f.read()
            self.signals.loaded.emit(data)
        except Exception as e:
            self.signals.failed.emit(str(e))

class Workers:
    pool = QThreadPool.globalInstance()

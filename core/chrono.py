# core/chrono.py
from PySide6.QtCore import QObject, QElapsedTimer, QTimer, Signal

class RealtimeTimer(QObject):
    elapsedChanged = Signal(float)  # seconds (active-time only)
    started = Signal()
    paused = Signal()
    resumed = Signal()
    stopped = Signal()

    def __init__(self, tick_ms: int = 100, parent=None):
        super().__init__(parent)
        self._elapsed = 0.0          # accumulated active seconds
        self._running = False
        self._paused = False
        self._t = QElapsedTimer()

        self._tick = QTimer(self)
        self._tick.setInterval(tick_ms)
        self._tick.timeout.connect(self._on_tick)

    def start(self):
        self._elapsed = 0.0
        self._paused = False
        self._running = True
        self._t.start()
        self._tick.start()
        self.started.emit()

    def pause(self):
        if self._running and not self._paused:
            self._elapsed += self._t.elapsed() / 1000.0
            self._paused = True
            self.paused.emit()

    def resume(self):
        if self._running and self._paused:
            self._paused = False
            self._t.restart()
            self.resumed.emit()

    def stop(self):
        if self._running:
            if not self._paused:
                self._elapsed += self._t.elapsed() / 1000.0
            self._running = False
            self._paused = False
            self._tick.stop()
            self.stopped.emit()

    def seconds(self) -> float:
        if self._running and not self._paused:
            return self._elapsed + (self._t.elapsed() / 1000.0)
        return self._elapsed

    def _on_tick(self):
        self.elapsedChanged.emit(self.seconds())

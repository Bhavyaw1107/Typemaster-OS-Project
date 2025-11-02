# ui/session_summary.py
from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
import pyqtgraph as pg


class SessionSummary(QDialog):
    """
    Displays final stats and a static WPM-over-time graph.
    """

    def __init__(
        self,
        wpm: float,
        acc: float,
        secs: float,
        times: list[float],
        wpms: list[float],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Session Summary")
        self.resize(720, 420)

        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"WPM: {wpm:.1f}"))
        root.addWidget(QLabel(f"Accuracy: {acc:.1f}%"))
        root.addWidget(QLabel(f"Time: {secs:.1f}s"))

        # Static plot (no live updates)
        plot = pg.PlotWidget()
        plot.setBackground(None)
        plot.setMenuEnabled(False)
        plot.setMouseEnabled(x=False, y=False)
        plot.hideButtons()
        plot.showGrid(x=False, y=True, alpha=0.08)
        plot.setLabel("left", "WPM")
        curve = plot.plot(times, wpms, pen=None, symbol="o", symbolSize=4)
        root.addWidget(plot, stretch=1)

        btn = QPushButton("OK", self)
        btn.clicked.connect(self.accept)
        root.addWidget(btn)

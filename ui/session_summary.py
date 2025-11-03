# ui/session_summary.py
from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
import pyqtgraph as pg
import math
from typing import Sequence
import bisect


def smooth_wpm_time_aware(
    timestamps: Sequence[float],
    raw_wpm: Sequence[float],
    tau_seconds: float = 2.5,
    blend_with_cumulative: bool = True,
    cumulative_weight: float = 0.25,
) -> list[float]:
    """
    Time-aware exponential smoothing (EMA) of WPM values.
    Preserves timestamps length. Suitable for instantaneous WPM series.
    """
    if not timestamps or not raw_wpm or len(timestamps) != len(raw_wpm):
        return list(raw_wpm)

    smoothed = [raw_wpm[0]]
    last_t = timestamps[0]

    for i in range(1, len(timestamps)):
        t = timestamps[i]
        dt = max(1e-6, t - last_t)
        last_t = t
        alpha = 1.0 - math.exp(-dt / float(tau_seconds))
        new_val = alpha * raw_wpm[i] + (1.0 - alpha) * smoothed[-1]
        smoothed.append(new_val)

    if blend_with_cumulative:
        cum = []
        s = 0.0
        for i, v in enumerate(raw_wpm):
            s += v
            cum.append(s / (i + 1))
        blended = [
            cumulative_weight * cum[i] + (1.0 - cumulative_weight) * smoothed[i]
            for i in range(len(smoothed))
        ]
        return blended

    return smoothed


def detect_cumulative_style(times: Sequence[float], wpms: Sequence[float]) -> bool:
    """
    Heuristic: returns True if series looks like cumulative-average WPM (bad for plotting).
    - Very large values at start (e.g. >1e4) OR
    - Strictly decreasing pattern that decays rapidly.
    """
    if not times or not wpms or len(times) != len(wpms):
        return False

    max_w = max(wpms)
    if max_w > 1e4:  # obvious blow-up (division by near zero elapsed time)
        return True

    # Check for rapid monotonic decay: count how many early samples drop more than 50%
    drops = 0
    check_len = min(len(wpms) - 1, 6)
    for i in range(check_len):
        if wpms[i] > 0 and wpms[i + 1] < 0.6 * wpms[i]:
            drops += 1
    if drops >= max(1, check_len // 3):
        return True

    return False


def convert_cumulative_wpm_to_instant(
    times: Sequence[float],
    cum_wpms: Sequence[float],
    window_seconds: float = 2.0,
) -> list[float]:
    """
    Convert cumulative-average WPM series into instantaneous WPM sampled over a moving window.
    """
    n = len(times)
    if n == 0 or n != len(cum_wpms):
        return [0.0] * len(cum_wpms)

    # Build estimated total chars at each sample
    total_chars = [0.0] * n
    for i, (t, w) in enumerate(zip(times, cum_wpms)):
        safe_t = max(1e-6, t)
        total_chars[i] = w * (5.0 * safe_t) / 60.0

    ts = list(times)
    inst = [0.0] * n
    for i in range(n):
        t_i = times[i]
        window_start = t_i - window_seconds
        j = bisect.bisect_left(ts, window_start)
        chars_in_window = total_chars[i] - (total_chars[j] if j >= 0 else 0.0)
        if chars_in_window < 0:
            chars_in_window = 0.0
        if window_seconds > 1e-6:
            inst[i] = (chars_in_window * 60.0) / (5.0 * window_seconds)
        else:
            inst[i] = 0.0

    return inst


class SessionSummary(QDialog):
    """
    Displays final stats and a static WPM-over-time graph.
    This version hides the faint dotted cumulative baseline.
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

        # Plot setup
        plot = pg.PlotWidget()
        plot.setBackground(None)
        plot.setMenuEnabled(False)
        plot.setMouseEnabled(x=False, y=False)
        plot.hideButtons()
        plot.showGrid(x=False, y=True, alpha=0.08)
        plot.setLabel("left", "WPM")
        plot.setLabel("bottom", "Time (s)")

        # Ensure lists are floats
        times = [float(t) for t in times]
        wpms = [float(v) for v in wpms]

        # If data looks like cumulative averages (common), convert to instant WPM
        if detect_cumulative_style(times, wpms):
            window_seconds = 2.0
            wpms_instant = convert_cumulative_wpm_to_instant(times, wpms, window_seconds=window_seconds)
        else:
            wpms_instant = wpms  # already instantaneous

        # Now smooth and optionally blend with cumulative baseline (but we won't plot the baseline)
        tau_seconds = 2.5
        blend_with_cumulative = True
        cumulative_weight = 0.25

        wpms_smoothed = smooth_wpm_time_aware(
            times,
            wpms_instant,
            tau_seconds=tau_seconds,
            blend_with_cumulative=blend_with_cumulative,
            cumulative_weight=cumulative_weight,
        )

        # Plot smoothed series (solid line only)
        plot.plot(
            times,
            wpms_smoothed,
            pen=pg.mkPen(color=(200, 200, 255), width=2),
            symbol=None,
        )

        # NOTE: The cumulative (dotted) baseline plotting was intentionally removed.
        # If you want it back later, re-add a plot like:
        # from PySide6 import QtCore
        # plot.plot(times, cum, pen=pg.mkPen(color=(80, 80, 100), width=1, style=QtCore.Qt.DashLine))

        root.addWidget(plot, stretch=1)

        btn = QPushButton("OK", self)
        btn.clicked.connect(self.accept)
        root.addWidget(btn)

# ui/weakkeys_dialog.py
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
)
from PySide6.QtCore import Qt
import csv
import pyqtgraph as pg


class WeakKeysDialog(QDialog):
    def __init__(self, weak_keys_ranked, parent=None):
        """
        weak_keys_ranked: iterable of tuples (key, miss_rate_float_0to1, hits, misses)
        """
        super().__init__(parent)
        self.setWindowTitle("Weak Keys")
        self.resize(680, 520)
        self._raw = list(weak_keys_ranked)
        self._filtered = self._raw[:]

        root = QVBoxLayout(self)

        # --- controls ---
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Min attempts:"))
        self.min_attempts = QSpinBox()
        self.min_attempts.setRange(0, 9999)
        self.min_attempts.setValue(3)
        self.min_attempts.valueChanged.connect(self._apply_filter)
        ctrl.addWidget(self.min_attempts)
        ctrl.addStretch(1)
        self.btn_export = QPushButton("Export CSV…")
        self.btn_export.clicked.connect(self._export_csv)
        ctrl.addWidget(self.btn_export)
        root.addLayout(ctrl)

        # --- plot (single item, reused) ---
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.showGrid(x=False, y=True, alpha=0.1)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.hideButtons()
        self.plot.setClipToView(True)  # <— added
        self.plot.enableAutoRange("y", True)  # <— added
        root.addWidget(self.plot, stretch=2)

        # persistent bar item (do NOT recreate each render)
        self._bar = pg.BarGraphItem(x=[], height=[], width=0.8)  # <— added
        self.plot.addItem(self._bar)  # <— added
        self._last_keys = None  # <— added

        # --- table ---
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Key", "Miss %", "Hits", "Misses"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, stretch=1)

        self._render()

    def _apply_filter(self):
        min_att = self.min_attempts.value()
        self._filtered = [r for r in self._raw if (r[2] + r[3]) >= min_att]
        self._render()

    def _render(self):
        # Build data arrays
        keys = [r[0] for r in self._filtered]
        rates = [int(round(r[1] * 100)) for r in self._filtered]  # 0..100 integers
        x = list(range(len(keys)))

        # Reuse the existing bar item instead of clearing/recreating
        self._bar.setOpts(x=x, height=rates, width=0.8)

        # Only rebuild bottom tick labels if the key set changed
        if keys != self._last_keys:
            self.plot.getAxis("bottom").setTicks([[(i, k) for i, k in enumerate(keys)]])
            self._last_keys = keys

        self.plot.setLabel("left", "Miss %")

        # Update table
        self.table.setRowCount(len(self._filtered))
        for i, (k, mr, hits, miss) in enumerate(self._filtered):
            self.table.setItem(i, 0, QTableWidgetItem(k))
            self.table.setItem(i, 1, QTableWidgetItem(f"{mr*100:.0f}%"))
            self.table.setItem(i, 2, QTableWidgetItem(str(hits)))
            self.table.setItem(i, 3, QTableWidgetItem(str(miss)))

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Weak Keys", "weak_keys.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Key", "MissPercent", "Hits", "Misses"])
            for k, mr, hits, miss in self._filtered:
                w.writerow([k, f"{mr*100:.0f}", hits, miss])

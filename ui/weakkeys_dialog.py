from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog
from PySide6.QtCore import Qt
import csv
import pyqtgraph as pg

class WeakKeysDialog(QDialog):
    def __init__(self, weak_keys_ranked, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Weak Keys")
        self.resize(680, 520)
        self._raw = list(weak_keys_ranked)
        self._filtered = self._raw[:]

        root = QVBoxLayout(self)

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

        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.showGrid(x=False, y=True, alpha=0.1)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.hideButtons()
        root.addWidget(self.plot, stretch=2)

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
        keys = [r[0] for r in self._filtered]
        rates = [int(round(r[1] * 100)) for r in self._filtered]
        x = list(range(len(keys)))

        self.plot.clear()
        bg = pg.BarGraphItem(x=x, height=rates, width=0.8)
        self.plot.addItem(bg)
        self.plot.getAxis('bottom').setTicks([[(i, k) for i, k in enumerate(keys)]])
        self.plot.setLabel('left', 'Miss %')

        self.table.setRowCount(len(self._filtered))
        for i, (k, mr, hits, miss) in enumerate(self._filtered):
            self.table.setItem(i, 0, QTableWidgetItem(k))
            self.table.setItem(i, 1, QTableWidgetItem(f"{mr*100:.0f}%"))
            self.table.setItem(i, 2, QTableWidgetItem(str(hits)))
            self.table.setItem(i, 3, QTableWidgetItem(str(miss)))

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Weak Keys", "weak_keys.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Key", "MissPercent", "Hits", "Misses"])
            for (k, mr, hits, miss) in self._filtered:
                w.writerow([k, f"{mr*100:.0f}", hits, miss])

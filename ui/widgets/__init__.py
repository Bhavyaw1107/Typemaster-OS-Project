# --- WPM live plot (one-time setup) ---
self.wpmPlot = pg.PlotWidget()
self.wpmPlot.setBackground(None)
self.wpmPlot.setMenuEnabled(False)
self.wpmPlot.setMouseEnabled(x=False, y=False)
self.wpmPlot.hideButtons()
self.wpmPlot.setDownsampling(mode='peak')
self.wpmPlot.setClipToView(True)
self.wpmPlot.showGrid(x=False, y=True, alpha=0.08)
self.wpmPlot.setLabel('left', 'WPM')

# keep a short rolling window to avoid unbounded arrays
self._wpm_time = deque(maxlen=600)   # ~60s at 10Hz
self._wpm_vals = deque(maxlen=600)

# a single, persistent curve — DO NOT recreate on each update
self._wpm_curve = self.wpmPlot.plot([], [], pen=None, symbol='o', symbolSize=4)

# add the widget to your layout (choose where it should appear)
self.layout().addWidget(self.wpmPlot)  # or root.addWidget(self.wpmPlot)

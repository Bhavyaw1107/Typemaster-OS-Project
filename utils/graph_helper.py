from typing import List
import pyqtgraph as pg

def setup_wpm_plot(plot_widget: pg.PlotWidget, line_color: str):
    plot_widget.setBackground(None)
    plot_widget.showGrid(x=False, y=True, alpha=0.15)
    plot_widget.setMenuEnabled(False)
    plot_widget.setMouseEnabled(x=False, y=False)
    plot_widget.hideButtons()
    plot_widget.setClipToView(True)
    plot_widget.getAxis('bottom').setTicks([])
    plot_widget.getAxis('left').setStyle(tickLength=-5)
    curve = plot_widget.plot([], [], pen=pg.mkPen(line_color, width=2.5), antialias=True)
    return curve

def update_curve(curve, y: List[float]):
    x = list(range(len(y)))
    curve.setData(x, y)

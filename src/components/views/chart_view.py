# src/components/views/chart_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg

class TelemetryChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.setTitle("Real-time Altitude", color='w', size='12pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Altitude (m)')
        self.plot_widget.setLabel('bottom', 'Packet Count')
        
        self.curve = self.plot_widget.plot(pen=pg.mkPen('#ffff00', width=2))
        self.data_x = []
        self.data_y = []
        self.ptr = 0
        layout.addWidget(self.plot_widget)
        
    def update_chart(self, data_list):
        if not data_list or len(data_list) < 6: return
        
        try:
            alt_val = float(data_list[5]) # Index 5 is Altitude
        except ValueError:
            return

        self.ptr += 1
        self.data_x.append(self.ptr)
        self.data_y.append(alt_val)
        
        # 최근 100개 데이터만 유지
        if len(self.data_x) > 100:
            self.data_x.pop(0)
            self.data_y.pop(0)
            
        self.curve.setData(self.data_x, self.data_y)
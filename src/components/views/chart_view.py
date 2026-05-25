from PyQt6.QtWidgets import QWidget, QGridLayout
import pyqtgraph as pg

class TelemetryChart(QWidget):
    def __init__(self):
        super().__init__()
        
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # 1. Altitude & Pressure 통합 차트
        self.plot_alt_press = pg.PlotWidget(title="Altitude [m] & Pressure [kPa]")
        self.plot_alt_press.showGrid(x=True, y=True, alpha=0.3)
        self.plot_alt_press.addLegend(offset=(5, 5))
        self.curve_alt = self.plot_alt_press.plot(pen=pg.mkPen('#2563eb', width=2), name="Alt")
        self.curve_press = self.plot_alt_press.plot(pen=pg.mkPen('#16a34a', width=2), name="Press")
        
        # 2. Battery [V] 차트 (Y축 지수 표기 방지를 위한 범위 고정)
        self.plot_volt = pg.PlotWidget(title="Battery [V]")
        self.plot_volt.showGrid(x=True, y=True, alpha=0.3)
        self.plot_volt.setYRange(0, 15, padding=0) # 배터리 전압 범위를 0~15V로 고정
        self.curve_volt = self.plot_volt.plot(pen=pg.mkPen('#9333ea', width=2))
        
        # 3. Temperature [°C] 차트
        self.plot_temp = pg.PlotWidget(title="Temperature [°C]")
        self.plot_temp.showGrid(x=True, y=True, alpha=0.3)
        self.curve_temp = self.plot_temp.plot(pen=pg.mkPen('#dc2626', width=2))
        
        # 4. Accelerometer [m/s²] 통합 차트
        self.plot_accel = pg.PlotWidget(title="Accelerometer [m/s²]")
        self.plot_accel.showGrid(x=True, y=True, alpha=0.3)
        self.plot_accel.addLegend(offset=(5, 5))
        self.curve_accel_x = self.plot_accel.plot(pen=pg.mkPen('#f59e0b', width=1), name="X")
        self.curve_accel_y = self.plot_accel.plot(pen=pg.mkPen('#10b981', width=1), name="Y")
        self.curve_accel_z = self.plot_accel.plot(pen=pg.mkPen('#6366f1', width=1), name="Z")

        # 5. Gyroscope [deg/s] 차트
        self.plot_gyro = pg.PlotWidget(title="Gyroscope [deg/s]")
        self.plot_gyro.showGrid(x=True, y=True, alpha=0.3)
        self.plot_gyro.addLegend(offset=(5, 5))
        self.curve_gyro_r = self.plot_gyro.plot(pen=pg.mkPen('r', width=1), name="Roll")
        self.curve_gyro_p = self.plot_gyro.plot(pen=pg.mkPen('g', width=1), name="Pitch")
        self.curve_gyro_y = self.plot_gyro.plot(pen=pg.mkPen('b', width=1), name="Yaw")

        # 6. GPS Data 차트 (고도 표시)
        self.plot_gps = pg.PlotWidget(title="GPS Altitude [m]")
        self.plot_gps.showGrid(x=True, y=True, alpha=0.3)
        self.curve_gps_alt = self.plot_gps.plot(pen=pg.mkPen('#4f46e5', width=1))

        self.layout.addWidget(self.plot_alt_press, 0, 0)
        self.layout.addWidget(self.plot_volt, 0, 1)
        self.layout.addWidget(self.plot_temp, 0, 2)
        self.layout.addWidget(self.plot_accel, 1, 0)
        self.layout.addWidget(self.plot_gyro, 1, 1)
        self.layout.addWidget(self.plot_gps, 1, 2)

        self.reset_data()

    def reset_data(self):
        attrs = ['data_cnt', 'data_alt', 'data_press', 'data_temp', 'data_volt', 
                 'data_gyro_r', 'data_gyro_p', 'data_gyro_y', 
                 'data_accel_x', 'data_accel_y', 'data_accel_z', 
                 'data_gps_lat', 'data_gps_lng', 'data_gps_alt']
        for attr in attrs:
            setattr(self, attr, [])

    def update_chart(self, data_list):
        # FSW 송신 데이터 개수(22개) 검증
        if not data_list or len(data_list) < 22: return
        
        def safe_float(val):
            try: return float(val)
            except: return 0.0

        try:
            # Teensy FSW main.cpp generateTelemetry()의 송신 순서와 100% 일치하는 인덱스
            cnt   = int(data_list[2])         # Index 2: PACKET_COUNT
            alt   = safe_float(data_list[5])  # Index 5: ALTITUDE
            temp  = safe_float(data_list[6])  # Index 6: TEMPERATURE
            press = safe_float(data_list[7])  # Index 7: PRESSURE
            volt  = safe_float(data_list[8])  # Index 8: VOLTAGE (Battery Voltage)
            
            # 자이로스코프 (Index 10, 11, 12)
            gr, gp, gy = map(safe_float, [data_list[10], data_list[11], data_list[12]])
            
            # 가속도계 (Index 13, 14, 15)
            ax, ay, az = map(safe_float, [data_list[13], data_list[14], data_list[15]])
            
            # GPS 데이터 (Index 17, 18, 19)
            g_alt = safe_float(data_list[17]) # GPS_ALTITUDE
            g_lat = safe_float(data_list[18]) # GPS_LATITUDE
            g_lng = safe_float(data_list[19]) # GPS_LONGITUDE
            
            # 데이터 리스트 누적
            self.data_cnt.append(cnt)
            self.data_alt.append(alt)
            self.data_press.append(press)
            self.data_temp.append(temp)
            self.data_volt.append(volt)
            self.data_gyro_r.append(gr)
            self.data_gyro_p.append(gp)
            self.data_gyro_y.append(gy)
            self.data_accel_x.append(ax)
            self.data_accel_y.append(ay)
            self.data_accel_z.append(az)
            self.data_gps_alt.append(g_alt)

            # 차트 실시간 업데이트
            self.curve_alt.setData(self.data_cnt, self.data_alt)
            self.curve_press.setData(self.data_cnt, self.data_press)
            self.curve_temp.setData(self.data_cnt, self.data_temp)
            self.curve_volt.setData(self.data_cnt, self.data_volt)
            self.curve_gyro_r.setData(self.data_cnt, self.data_gyro_r)
            self.curve_gyro_p.setData(self.data_cnt, self.data_gyro_p)
            self.curve_gyro_y.setData(self.data_cnt, self.data_gyro_y)
            self.curve_accel_x.setData(self.data_cnt, self.data_accel_x)
            self.curve_accel_y.setData(self.data_cnt, self.data_accel_y)
            self.curve_accel_z.setData(self.data_cnt, self.data_accel_z)
            self.curve_gps_alt.setData(self.data_cnt, self.data_gps_alt)

            # X축 자동 범위 설정
            for plot in [self.plot_alt_press, self.plot_volt, self.plot_temp, 
                         self.plot_accel, self.plot_gyro, self.plot_gps]:
                plot.enableAutoRange(axis='x', enable=True)

        except Exception as e:
            print(f"Chart Update Error: {e}")
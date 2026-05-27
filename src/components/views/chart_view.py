from PyQt6.QtWidgets import QWidget, QGridLayout
import pyqtgraph as pg

# 전역 설정은 모듈 레벨에서 1회만 (인스턴스 생성마다 덮어쓰기 방지)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class TelemetryChart(QWidget):

    def __init__(self):
        super().__init__()

        grid = QGridLayout(self)   # self.layout → grid (내장 layout() 메서드 이름 충돌 방지)
        grid.setContentsMargins(5, 5, 5, 5)
        grid.setSpacing(5)

        def make_plot(title):
            p = pg.PlotWidget(title=title)
            p.showGrid(x=True, y=True, alpha=0.3)
            p.setMouseEnabled(x=True, y=True)
            return p

        # ── 차트 생성 ──────────────────────────────────────────
        self.plot_alt_press = make_plot("Altitude [m] & Pressure [kPa]")
        self.plot_alt_press.addLegend(offset=(5, 5))
        self.curve_alt   = self.plot_alt_press.plot(pen=pg.mkPen('#2563eb', width=2), name="Alt")
        self.curve_press = self.plot_alt_press.plot(pen=pg.mkPen('#16a34a', width=2), name="Press")

        self.plot_volt = make_plot("Battery [V]")
        self.plot_volt.setYRange(0, 15, padding=0)
        self.curve_volt = self.plot_volt.plot(pen=pg.mkPen('#9333ea', width=2))

        self.plot_temp = make_plot("Temperature [°C]")
        self.curve_temp = self.plot_temp.plot(pen=pg.mkPen('#dc2626', width=2))

        self.plot_accel = make_plot("Accelerometer [deg/s²]")
        self.plot_accel.addLegend(offset=(5, 5))
        self.curve_accel_x = self.plot_accel.plot(pen=pg.mkPen('#f59e0b', width=1), name="R")
        self.curve_accel_y = self.plot_accel.plot(pen=pg.mkPen('#10b981', width=1), name="P")
        self.curve_accel_z = self.plot_accel.plot(pen=pg.mkPen('#6366f1', width=1), name="Y")

        self.plot_gyro = make_plot("Gyroscope [deg/s]")
        self.plot_gyro.addLegend(offset=(5, 5))
        self.curve_gyro_r = self.plot_gyro.plot(pen=pg.mkPen('r', width=1), name="Roll")
        self.curve_gyro_p = self.plot_gyro.plot(pen=pg.mkPen('g', width=1), name="Pitch")
        self.curve_gyro_y = self.plot_gyro.plot(pen=pg.mkPen('b', width=1), name="Yaw")

        self.plot_gps = make_plot("GPS Altitude [m]")
        self.curve_gps_alt = self.plot_gps.plot(pen=pg.mkPen('#4f46e5', width=1))

        self._all_plots = [
            self.plot_alt_press, self.plot_volt, self.plot_temp,
            self.plot_accel, self.plot_gyro, self.plot_gps,
        ]

        # X축 AutoRange는 초기화 시 한 번만 설정 (매 업데이트마다 재호출 불필요)
        for p in self._all_plots:
            p.enableAutoRange(axis='x', enable=True)

        grid.addWidget(self.plot_alt_press, 0, 0)
        grid.addWidget(self.plot_volt,      0, 1)
        grid.addWidget(self.plot_temp,      0, 2)
        grid.addWidget(self.plot_accel,     1, 0)
        grid.addWidget(self.plot_gyro,      1, 1)
        grid.addWidget(self.plot_gps,       1, 2)

        self._reset_buffers()

    # ── 내부 데이터 버퍼 ─────────────────────────────────────────

    def _reset_buffers(self):
        (self.data_cnt, self.data_alt, self.data_press, self.data_temp,
         self.data_volt, self.data_gyro_r, self.data_gyro_p, self.data_gyro_y,
         self.data_accel_x, self.data_accel_y, self.data_accel_z,
         self.data_gps_alt) = ([] for _ in range(12))

    # ── 차트 업데이트 ────────────────────────────────────────────

    def update_chart(self, data_list):
        if not data_list or len(data_list) < 22:
            return

        def safe_float(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        try:
            cnt   = int(data_list[2])
            alt   = safe_float(data_list[5])
            temp  = safe_float(data_list[6])
            press = safe_float(data_list[7])
            volt  = safe_float(data_list[8])
            gr, gp, gy = safe_float(data_list[10]), safe_float(data_list[11]), safe_float(data_list[12])
            ax, ay, az = safe_float(data_list[13]), safe_float(data_list[14]), safe_float(data_list[15])
            g_alt = safe_float(data_list[17])

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

        except Exception as e:
            print(f"[ChartView] update error: {e}")

    # ── 초기화 (main_window IDLE 전환 시 호출) ──────────────────

    def clear_chart(self):
        self._reset_buffers()
        for curve in [self.curve_alt, self.curve_press, self.curve_temp,
                      self.curve_volt, self.curve_gyro_r, self.curve_gyro_p,
                      self.curve_gyro_y, self.curve_accel_x, self.curve_accel_y,
                      self.curve_accel_z, self.curve_gps_alt]:
            curve.setData([], [])
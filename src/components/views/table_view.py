from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt


class TelemetryTable(QTableWidget):

    HEADERS = [
        "TEAM_ID",       # 1.  Team ID
        "MISSION_TIME",  # 2.  UTC Time
        "PACKET_COUNT",  # 3.  Total Count
        "MODE",          # 4.  F or S
        "STATE",         # 5.  Software State
        "ALTITUDE",      # 6.  Relative Altitude [m]
        "TEMPERATURE",   # 7.  Temperature [°C]
        "PRESSURE",      # 8.  Pressure [kPa]
        "VOLTAGE",       # 9.  Bus Voltage [V]
        "CURRENT",       # 10. Battery Current [A]
        "GYRO_R",        # 11. Gyro Roll [deg/s]
        "GYRO_P",        # 11. Gyro Pitch [deg/s]
        "GYRO_Y",        # 11. Gyro Yaw [deg/s]
        "ACCEL_R",       # 12. Accel Roll [deg/s²]
        "ACCEL_P",       # 12. Accel Pitch [deg/s²]
        "ACCEL_Y",       # 12. Accel Yaw [deg/s²]
        "GPS_TIME",      # 13. GPS Time
        "GPS_ALTITUDE",  # 14. GPS Altitude [m]
        "GPS_LATITUDE",  # 15. GPS Latitude [deg]
        "GPS_LONGITUDE", # 16. GPS Longitude [deg]
        "GPS_SATS",      # 17. Satellites Count
        "CMD_ECHO",      # 18. Last Command
    ]
    _COL_COUNT = len(HEADERS)

    def __init__(self):
        super().__init__()

        self.setColumnCount(self._COL_COUNT)
        self.setHorizontalHeaderLabels(self.HEADERS)

        # 초기 한 번만 ResizeToContents, 이후 Interactive로 전환 (성능)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # 사용자가 스크롤 중인지 추적
        self._auto_scroll = True
        vbar = self.verticalScrollBar()
        vbar.valueChanged.connect(self._on_scroll_changed)
        vbar.rangeChanged.connect(self._on_range_changed)

    # ── 스크롤 자동/수동 전환 ────────────────────────────────────

    def _on_scroll_changed(self, value):
        """사용자가 맨 아래가 아닌 곳으로 스크롤하면 자동 스크롤 해제"""
        vbar = self.verticalScrollBar()
        self._auto_scroll = (value == vbar.maximum())

    def _on_range_changed(self, _min, _max):
        """새 행 추가로 범위가 늘어날 때, 자동 스크롤 모드면 따라 내려감"""
        if self._auto_scroll:
            self.verticalScrollBar().setValue(_max)

    # ── 데이터 추가 ──────────────────────────────────────────────

    def add_data(self, data_list):
        if not data_list or len(data_list) < self._COL_COUNT:
            return

        # 첫 행 추가 시 컬럼 너비 고정 (이후 매 행마다 재계산 방지)
        if self.rowCount() == 0:
            self.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive)

        row_idx = self.rowCount()
        self.insertRow(row_idx)

        for col in range(self._COL_COUNT):
            item = QTableWidgetItem(str(data_list[col]).strip())
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, col, item)

    # ── 검색 ─────────────────────────────────────────────────────

    def search_time_and_scroll(self, target_time):
        self.clearSelection()
        for row in range(self.rowCount()):
            item = self.item(row, 1)  # MISSION_TIME 컬럼
            if item and target_time in item.text():
                self.selectRow(row)
                self.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                self._auto_scroll = False  # 검색 후 자동 스크롤 일시 해제
                break

    # ── 초기화 ───────────────────────────────────────────────────

    def clear_table(self):
        self.setRowCount(0)
        self._auto_scroll = True
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
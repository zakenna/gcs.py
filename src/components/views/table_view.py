from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt

class TelemetryTable(QTableWidget):
    def __init__(self):
        super().__init__()
        
        # [요구사항 1~18 반영 헤더]
        self.headers = [
            "TEAM_ID",          # 1. Team ID
            "MISSION_TIME",     # 2. UTC Time
            "PACKET_COUNT",     # 3. Total Count
            "MODE",             # 4. F or S
            "STATE",            # 5. Software State
            "ALTITUDE",         # 6. Relative Altitude
            "TEMPERATURE",      # 7. Temperature
            "PRESSURE",         # 8. Pressure (kPa)
            "VOLTAGE",          # 9. Bus Voltage
            "CURRENT",          # 10. Battery Current
            "GYRO_R",           # 11. Gyro Roll
            "GYRO_P",           # 11. Gyro Pitch
            "GYRO_Y",           # 11. Gyro Yaw
            "ACCEL_R",          # 12. Accel Roll
            "ACCEL_P",          # 12. Accel Pitch
            "ACCEL_Y",          # 12. Accel Yaw
            "GPS_TIME",         # 13. GPS Time
            "GPS_ALTITUDE",     # 14. GPS Altitude
            "GPS_LATITUDE",     # 15. GPS Latitude
            "GPS_LONGITUDE",    # 16. GPS Longitude
            "GPS_SATS",         # 17. Satellites Count
            "CMD_ECHO"          # 18. Last Command
        ]
        
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def add_data(self, data_list):
        # 데이터 개수 체크 (22개 컬럼)
        if not data_list or len(data_list) < 22:
            return

        row_idx = self.rowCount()
        self.insertRow(row_idx)

        for i in range(len(self.headers)):
            if i < len(data_list):
                val = str(data_list[i]).strip()
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_idx, i, item)
            else:
                self.setItem(row_idx, i, QTableWidgetItem(""))
        
        self.scrollToBottom()
        
    def search_time_and_scroll(self, target_time):
        row_count = self.rowCount()
        self.clearSelection()

        for row in range(row_count):
            item = self.item(row, 1) 
            if item and target_time in item.text():
                self.selectRow(row) 
                self.scrollToItem(item, self.ScrollHint.PositionAtCenter)
                break 
    
    def clear_table(self):
        self.setRowCount(0)
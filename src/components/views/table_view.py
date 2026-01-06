from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt

class TelemetryTable(QTableWidget):
    def __init__(self):
        super().__init__()
        
        # 1. 미션 요구사항 3.1.1.1에 맞춘 헤더 정의 (총 22개)
        self.headers = [
            "TEAM_ID", "MISSION_TIME", "PACKET_COUNT", "MODE", "STATE", "ALTITUDE",
            "TEMPERATURE", "PRESSURE", "VOLTAGE", "CURRENT", "GYRO_R", "GYRO_P",
            "GYRO_Y", "ACCEL_R", "ACCEL_P", "ACCEL_Y", "GPS_TIME", "GPS_ALTITUDE",
            "GPS_LATITUDE", "GPS_LONGITUDE", "GPS_SATS", "CMD_ECHO"
        ]
        
        # 2. 컬럼 설정
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        
        # 3. 컬럼 너비 설정 (내용에 맞게 자동 조절 + 가로 스크롤)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # 스타일 설정
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def add_data(self, data_list):
        """
        data_list: 백엔드에서 넘어온 리스트
        요구사항에 따라 최소 22개의 데이터가 있어야 정상 처리
        """
        if not data_list or len(data_list) < 22:
            return

        row_idx = self.rowCount()
        self.insertRow(row_idx)

        # 데이터 매핑
        for i in range(len(self.headers)):
            if i < len(data_list):
                val = str(data_list[i]).strip()
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_idx, i, item)
        
        self.scrollToBottom()
        
    def search_time_and_scroll(self, target_time):
        """
        특정 시간(문자열)을 포함하는 행을 찾아 포커스 이동
        Target Column: 1번 인덱스 (MISSION_TIME)
        """
        # 테이블 전체 행을 스캔
        row_count = self.rowCount()
        found = False
        
        # 기존 선택 해제
        self.clearSelection()

        for row in range(row_count):
            # 1번 컬럼(MISSION_TIME)의 아이템을 가져옴
            item = self.item(row, 1) 
            if item and target_time in item.text():
                # 찾았다!
                self.selectRow(row) # 해당 행 선택(파란색 하이라이트)
                self.scrollToItem(item, self.ScrollHint.PositionAtCenter) # 화면 중앙으로 스크롤 이동
                found = True
                print(f"🔍 검색 성공: Row {row} -> {item.text()}")
                break # 첫 번째 발견된 곳에서 멈춤
        
        if not found:
            print(f"⚠️ 검색 실패: '{target_time}'을(를) 찾을 수 없습니다.")

    def clear_table(self):
        self.setRowCount(0)
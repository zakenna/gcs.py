import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QPushButton, QStackedWidget, QLineEdit, 
                             QLabel, QMessageBox)
from PyQt6.QtCore import Qt

from src.backend import GCSBackend, SIM_STATE
from src.components.header import HeaderWidget
from src.components.sidebar import SidebarWidget
from src.components.views.table_view import TelemetryTable
from src.components.views.chart_view import TelemetryChart
from src.components.views.echo_view import EchoTerminal

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCS - Team CosmoLink (Real Backend)")
        self.resize(1280, 800)
        self.setStyleSheet("background-color: #f3f4f6;") 

        # 1. 백엔드 인스턴스 생성
        self.backend = GCSBackend()

        # 2. UI 레이아웃 구성
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        self.header = HeaderWidget()
        main_layout.addWidget(self.header)

        # Body (Sidebar + Content)
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        
        # 여백 10px 최적화
        body_layout.setContentsMargins(10, 10, 10, 10) 
        body_layout.setSpacing(10)

        # Sidebar
        self.sidebar = SidebarWidget(self.backend)
        body_layout.addWidget(self.sidebar)

        # Content Wrapper
        self.content_wrapper = QFrame()
        self.content_wrapper.setStyleSheet("""
            .QFrame { 
                background-color: #ffffff; 
                border: 1px solid #d1d5db; 
                border-radius: 16px; 
                border-top-right-radius: 0px; 
                border-bottom-right-radius: 0px; 
            }
        """)
        wrapper_layout = QVBoxLayout(self.content_wrapper)
        wrapper_layout.setContentsMargins(15, 15, 15, 15)

        # ========================================================
        # [툴바 영역]
        # ========================================================
        btn_toolbar = QHBoxLayout()
        
        # (1) 기본 명령어 버튼들
        btn_calib = QPushButton("CALIBRATE")
        btn_cx_on = QPushButton("CX ON")
        btn_cx_off = QPushButton("CX OFF")
        btn_set_time = QPushButton("SET TIME")
        
        for btn in [btn_calib, btn_cx_on, btn_cx_off, btn_set_time]:
            btn.setStyleSheet("""
                QPushButton { background: white; border: 1px solid #d1d5db; padding: 6px 12px; font-weight: bold; border-radius: 4px; } 
                QPushButton:hover { background: #f3f4f6; }
            """)
            btn_toolbar.addWidget(btn)
        
        # (2) MEC ON 버튼 (강조)
        self.btn_mec_on = QPushButton("MEC ON")
        self.btn_mec_on.setStyleSheet("""
            QPushButton { 
                background-color: #7c3aed; color: white; font-weight: bold; 
                border: 1px solid #6d28d9; padding: 6px 12px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #6d28d9; }
            QPushButton:pressed { background-color: #5b21b6; }
        """)
        btn_toolbar.addWidget(self.btn_mec_on)

        # (3) 중간 여백
        btn_toolbar.addStretch()

        # (4) 검색 UI
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Find Time (e.g. 11:24:57)")
        self.input_search.setFixedWidth(180)
        self.input_search.setStyleSheet("padding: 5px; border: 1px solid #d1d5db; border-radius: 4px;")
        
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedWidth(40)
        self.btn_search.setStyleSheet("background-color: #2563eb; color: white; border: none; border-radius: 4px; font-weight: bold;")

        btn_toolbar.addWidget(self.input_search)
        btn_toolbar.addWidget(self.btn_search)
        
        wrapper_layout.addLayout(btn_toolbar)

        # --------------------------------------------------------
        # 기능 연결
        # --------------------------------------------------------
        btn_calib.clicked.connect(self.backend.cmd_calibrate)
        btn_cx_on.clicked.connect(self.backend.cmd_cx_on)
        btn_cx_off.clicked.connect(self.backend.cmd_cx_off)
        btn_set_time.clicked.connect(self.backend.cmd_set_time)
        self.btn_mec_on.clicked.connect(self.confirm_mec_on)

        self.input_search.returnPressed.connect(self.execute_search)
        self.btn_search.clicked.connect(self.execute_search)

        # Views Stack
        self.container = QStackedWidget()
        self.view_table = TelemetryTable()
        self.view_chart = TelemetryChart()
        self.view_echo = EchoTerminal()

        self.container.addWidget(self.view_table)
        self.container.addWidget(self.view_chart)
        self.container.addWidget(self.view_echo)
        
        wrapper_layout.addWidget(self.container)
        body_layout.addWidget(self.content_wrapper)
        main_layout.addWidget(body_widget)

        # Signal-Slot 연결
        self.sidebar.view_changed.connect(self.change_view)
        self.backend.data_received.connect(self.on_data_received)
        self.backend.log_received.connect(self.view_echo.append_log)
        self.backend.state_changed.connect(self.on_state_changed)

    # ============================================================
    # 메서드 정의
    # ============================================================
    def change_view(self, view_name):
        if view_name == "table": self.container.setCurrentIndex(0)
        elif view_name == "chart": self.container.setCurrentIndex(1)
        elif view_name == "echo": self.container.setCurrentIndex(2)

    def on_data_received(self, data):
        # 1. Table 추가
        self.view_table.add_data(data)
        
        # 2. Chart 업데이트
        self.view_chart.update_chart(data)
        
        # 3. Header Packet Count 업데이트
        self.header.update_packet_count(self.backend.packet_count)
        
        # 4. Sidebar GPS 텍스트 업데이트
        self.sidebar.update_gps_data() 
        
        # 5. [수정] Map 업데이트 인덱스 교정
        try:
            # Sender.py 기준: 17=Lat, 18=Lng
            lat = float(data[17]) 
            lng = float(data[18])
            
            if lat != 0 and lng != 0:
                self.sidebar.map_view.update_map(lat, lng)
        except:
            pass
        
    def on_state_changed(self, new_state):
        if new_state == SIM_STATE["IDLE"]:
            self.view_table.clear_table() 
            self.view_chart.clear_chart() 
            self.input_search.clear() 

    def execute_search(self):
        target = self.input_search.text().strip()
        if not target:
            return
        
        if self.container.currentIndex() == 0: 
            self.view_table.search_time_and_scroll(target)
        else:
            print("⚠️ 검색은 Table View에서만 가능합니다.")

    def confirm_mec_on(self):
        reply = QMessageBox.question(
            self, 
            "⚠️ Critical Command Warning", 
            "MEC ON (Mechanism Activation) 명령을 전송하시겠습니까?\n\n"
            "이 명령은 낙하산 전개 또는 모듈 분리를 유발하며,\n"
            "실행 후에는 되돌릴 수 없습니다!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.backend.cmd_mec_on()

    def closeEvent(self, event):
        if self.backend.worker.isRunning():
            self.backend.worker.stop()
        event.accept()
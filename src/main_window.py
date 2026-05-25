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
        self.setWindowTitle("GCS - Team CosmoLink (Real FSW Interface)")
        self.resize(1280, 800)
        self.setStyleSheet("background-color: #f3f4f6;") 

        self.backend = GCSBackend()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.header = HeaderWidget()
        main_layout.addWidget(self.header)

        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10) 
        body_layout.setSpacing(10)

        self.sidebar = SidebarWidget(self.backend)
        body_layout.addWidget(self.sidebar)

        self.content_wrapper = QFrame()
        self.content_wrapper.setStyleSheet("""
            .QFrame { background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 16px; border-top-right-radius: 0px; border-bottom-right-radius: 0px; }
        """)
        wrapper_layout = QVBoxLayout(self.content_wrapper)
        wrapper_layout.setContentsMargins(15, 15, 15, 15)

        # 상단 툴바 구성
        btn_toolbar = QHBoxLayout()
        btn_calib = QPushButton("CALIBRATE")
        btn_cx_on = QPushButton("CX ON")
        btn_cx_off = QPushButton("CX OFF")
        btn_set_time = QPushButton("SET TIME")
        
        # 서보모터 구동 상태 플래그 초기화 (False: 꺼짐, True: 켜짐)
        self.mec_servo_active = False 
        
        for btn in [btn_calib, btn_cx_on, btn_cx_off, btn_set_time]:
            btn.setStyleSheet("QPushButton { background: white; border: 1px solid #d1d5db; padding: 6px 12px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background: #f3f4f6; }")
            btn_toolbar.addWidget(btn)
        
        # 버튼을 상태에 따라 동적으로 제어할 수 있도록 인스턴스 명시 변경
        self.btn_mec_toggle = QPushButton("MEC SERVO ON")
        self.btn_mec_toggle.setStyleSheet("QPushButton { background: white; border: 1px solid #d1d5db; padding: 6px 12px; font-weight: bold; border-radius: 4px; color: #1e293b; } QPushButton:hover { background: #f3f4f6; }")
        btn_toolbar.addWidget(self.btn_mec_toggle)

        btn_toolbar.addStretch()

        # 검색 UI 검색창 패널
        self.search_pill = QFrame()
        self.search_pill.setFixedSize(280, 42) 
        self.search_pill.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                                                  stop:0 #ffffff, stop:1 #f3f4f6);
                border: 1px solid #d1d5db;
                border-radius: 21px; 
            }
            QFrame:hover {
                border: 1px solid #3b82f6; 
                background-color: #ffffff;
            }
        """)
        
        pill_layout = QHBoxLayout(self.search_pill)
        pill_layout.setContentsMargins(15, 0, 5, 0)
        pill_layout.setSpacing(5)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Find Time (e.g. 12:00:00)")
        self.input_search.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 13px;
                color: #1f2937;
            }
        """)
        
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(32, 32)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                color: #6b7280;
                font-size: 16px;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                color: #2563eb;
            }
        """)

        pill_layout.addWidget(self.input_search)
        pill_layout.addWidget(self.btn_search)
        btn_toolbar.addWidget(self.search_pill)

        wrapper_layout.addLayout(btn_toolbar)

        # 슬롯 신호 라우팅 매핑 체결
        btn_calib.clicked.connect(self.backend.cmd_calibrate)
        btn_cx_on.clicked.connect(self.backend.cmd_cx_on)
        btn_cx_off.clicked.connect(self.backend.cmd_cx_off)
        btn_set_time.clicked.connect(self.backend.cmd_set_time)
        self.btn_mec_toggle.clicked.connect(self.handle_mec_toggle)
        self.input_search.returnPressed.connect(self.execute_search)
        self.btn_search.clicked.connect(self.execute_search)

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

        self.sidebar.view_changed.connect(self.change_view)
        self.backend.data_received.connect(self.on_data_received)
        self.backend.log_received.connect(self.view_echo.append_log)
        self.backend.state_changed.connect(self.on_state_changed)

    def change_view(self, view_name):
        if view_name == "table": self.container.setCurrentIndex(0)
        elif view_name == "chart": self.container.setCurrentIndex(1)
        elif view_name == "echo": self.container.setCurrentIndex(2)

    def on_data_received(self, data):
        self.view_table.add_data(data)
        self.view_chart.update_chart(data)
        self.header.update_packet_count(self.backend.packet_count)
        
    def on_state_changed(self, new_state):
        if new_state == SIM_STATE["IDLE"]:
            self.view_table.clear_table() 
            self.view_chart.clear_chart() 
            self.input_search.clear() 

    def execute_search(self):
        target = self.input_search.text().strip()
        if not target: return
        if self.container.currentIndex() == 0: 
            self.view_table.search_time_and_scroll(target)

    def handle_mec_toggle(self):
        """Teensy FSW 파서 토큰 구조에 부합되게 완전히 재구축된 양방향 제어 토글 시퀀스"""
        if not self.mec_servo_active:
            reply = QMessageBox.question(self, "MEC ON Warning", "Teensy FSW 서보모터를 활성화(MEC ON) 하시겠습니까?", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.backend.cmd_mec_servo_on()
                self.mec_servo_active = True
                self.btn_mec_toggle.setText("MEC SERVO OFF")
                self.btn_mec_toggle.setStyleSheet("QPushButton { background: #fee2e2; border: 1px solid #fca5a5; padding: 6px 12px; font-weight: bold; color: #dc2626; border-radius: 4px; } QPushButton:hover { background: #ffeeee; }")
        else:
            reply = QMessageBox.question(self, "MEC OFF Warning", "Teensy FSW 서보모터를 비활성화(MEC OFF) 하시겠습니까?", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.backend.cmd_mec_servo_off()
                self.mec_servo_active = False
                self.btn_mec_toggle.setText("MEC SERVO ON")
                self.btn_mec_toggle.setStyleSheet("QPushButton { background: white; border: 1px solid #d1d5db; padding: 6px 12px; font-weight: bold; color: #1e293b; border-radius: 4px; } QPushButton:hover { background: #f3f4f6; }")

    def closeEvent(self, event):
        if self.backend.worker.isRunning():
            self.backend.worker.stop()
        event.accept()
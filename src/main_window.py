import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QFrame, QPushButton, QStackedWidget, QLineEdit, QLabel)
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

        # ── 상단 툴바 ────────────────────────────────────────────
        btn_toolbar = QHBoxLayout()
        _btn_style = ("QPushButton { background:white; border:1px solid #d1d5db; "
                      "padding:6px 12px; font-weight:bold; border-radius:4px; } "
                      "QPushButton:hover { background:#f3f4f6; }")

        for label, slot in [
            ("CALIBRATE", self.backend.cmd_calibrate),
            ("CX ON",     self.backend.cmd_cx_on),
            ("CX OFF",    self.backend.cmd_cx_off),
            ("SET TIME",  self.backend.cmd_set_time),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(_btn_style)
            btn.clicked.connect(slot)
            btn_toolbar.addWidget(btn)

        btn_toolbar.addStretch()

        # ── 검색 필드 ────────────────────────────────────────────
        self.search_pill = QFrame()
        self.search_pill.setFixedSize(280, 42)
        self.search_pill.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f3f4f6);
                border: 1px solid #d1d5db;
                border-radius: 21px;
            }
            QFrame:hover { border: 1px solid #3b82f6; background-color: #ffffff; }
        """)
        pill_layout = QHBoxLayout(self.search_pill)
        pill_layout.setContentsMargins(15, 0, 5, 0)
        pill_layout.setSpacing(5)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Find Time (e.g. 12:00:00)")
        self.input_search.setStyleSheet(
            "QLineEdit { border:none; background:transparent; font-size:13px; color:#1f2937; }")

        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(32, 32)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setStyleSheet("""
            QPushButton { border:none; background:transparent; color:#6b7280;
                          font-size:16px; border-radius:16px; }
            QPushButton:hover { background:#e5e7eb; color:#2563eb; }
        """)
        pill_layout.addWidget(self.input_search)
        pill_layout.addWidget(self.btn_search)
        btn_toolbar.addWidget(self.search_pill)

        wrapper_layout.addLayout(btn_toolbar)

        # ── 뷰 컨테이너 ──────────────────────────────────────────
        self.container   = QStackedWidget()
        self.view_table  = TelemetryTable()
        self.view_chart  = TelemetryChart()
        self.view_echo   = EchoTerminal()

        self.container.addWidget(self.view_table)   # index 0
        self.container.addWidget(self.view_chart)   # index 1
        self.container.addWidget(self.view_echo)    # index 2

        wrapper_layout.addWidget(self.container)
        body_layout.addWidget(self.content_wrapper)
        main_layout.addWidget(body_widget)

        # ── 시그널 배선 ──────────────────────────────────────────
        self.sidebar.view_changed.connect(self.change_view)
        self.input_search.returnPressed.connect(self.execute_search)
        self.btn_search.clicked.connect(self.execute_search)
        self.backend.data_received.connect(self.on_data_received)
        self.backend.log_received.connect(self.view_echo.append_log)
        self.backend.state_changed.connect(self.on_state_changed)

    _VIEW_MAP = {"chart": 1, "table": 0, "echo": 2}

    def change_view(self, view_name):
        idx = self._VIEW_MAP.get(view_name)
        if idx is not None:
            self.container.setCurrentIndex(idx)

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
        if target and self.container.currentIndex() == 0:
            self.view_table.search_time_and_scroll(target)

    def closeEvent(self, event):
        if self.backend.worker.isRunning():
            self.backend.worker.stop()
        event.accept()
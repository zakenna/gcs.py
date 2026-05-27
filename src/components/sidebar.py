from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QWidget, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from src.backend import SIM_STATE, TEAM_ID

# Telemetry Units 표시 상수 (클래스 레벨, 초기화 시 재계산 불필요)
_TELEMETRY_ENTRIES = [
    ("ALTITUDE",      "[m]"),
    ("TEMPERATURE",   "[°C]"),
    ("PRESSURE",      "[kPa]"),
    ("VOLTAGE",       "[V]"),
    ("CURRENT",       "[A]"),
    ("GYRO (R,P,Y)",  "[deg/s]"),
    ("ACCEL (R,P,Y)", "[deg/s²]"),
    ("GPS_ALTITUDE",  "[m]"),
    ("GPS_LAT/LNG",   "[deg]"),
]
_TOTAL_CHARS = 30  # 사이드바 188px ÷ Consolas 11px(≈6.6px) ≈ 28자 + 불릿 2자

def _build_telemetry_html():
    """모듈 로드 시 1회만 계산, 이후 재사용"""
    def make_row(label, unit):
        prefix = f"• {label}: "
        dots = "·" * max(2, _TOTAL_CHARS - len(prefix) - 1 - len(unit))
        line = (f"{prefix}<span style='color:#9ca3af;'>{dots}</span>"
                f" <b style='color:#1d4ed8;'>{unit}</b>")
        return f"<div style='line-height:1.4;'>{line}</div>"
    return "".join(make_row(lbl, u) for lbl, u in _TELEMETRY_ENTRIES)

_TELEMETRY_HTML = _build_telemetry_html()  # 모듈 임포트 시 딱 1회 생성

# 상태별 스타일 매핑 (update_display 호출마다 dict 조회로 분기 제거)
_STATE_STYLES = {
    "RUNNING":  ("SIMULATION MODE", "color:#c2410c; background-color:#fff7ed; border:1px solid #fdba74;"),
    "LOADED":   ("SIMULATION READY","color:#ea580c; background-color:#fffbeb; border:1px solid #fde68a;"),
    "ENABLED":  ("SIMULATION READY","color:#ea580c; background-color:#fffbeb; border:1px solid #fde68a;"),
}
_STYLE_CONNECTED = ("REAL MODE","color:#15803d; background-color:#dcfce7; border:1px solid #86efac;")
_STYLE_IDLE      = ("NONE",     "color:#6b7280; background-color:#f3f4f6; border:1px solid #e5e7eb;")
_STATUS_BASE = "font-family:'Consolas',monospace; font-size:11px; font-weight:bold; padding:10px; border-radius:6px; line-height:1.6;"


class SidebarWidget(QFrame):
    view_changed = pyqtSignal(str)

    def __init__(self, backend_ref):
        super().__init__()
        self.backend = backend_ref

        # 패킷 유실 계산용 내부 상태
        self.current_cmd_log  = "NONE"
        self.last_cansat_state = "LAUNCH_PAD"
        self.last_packet_num  = -1
        self.lost_packets_count = 0
        self._last_style = ""   # 중복 setStyleSheet 방지용 캐시

        self.setFixedWidth(240)
        self.setStyleSheet("""
            SidebarWidget {
                background-color: #f9fafb;
                border-right: 1px solid #d1d5db;
                border-top-right-radius: 16px;
                border-bottom-right-radius: 16px;
            }
            QLabel { color: #1f2937; }
            QPushButton {
                border-radius: 6px; padding: 0px; font-size: 12px; font-weight: bold;
                border: 1px solid #d1d5db; background-color: white;
            }
            QPushButton:hover    { background-color: #f3f4f6; }
            QPushButton:disabled { background-color: #f3f4f6; color: #9ca3af; border: 1px solid #e5e7eb; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 25, 16, 25)
        layout.setSpacing(0)

        header_style = "border-bottom: 1px solid #d1d5db; padding-bottom: 5px; margin-bottom: 5px;"
        header_font  = QFont("Segoe UI", 10, QFont.Weight.Bold)

        # ── [1] Control Panel ────────────────────────────────────
        control_group  = QWidget()
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)

        lbl_cp = QLabel("Control Panel")
        lbl_cp.setFont(header_font)
        lbl_cp.setStyleSheet(header_style)

        self.lbl_status_display = QLabel()
        self.lbl_status_display.setWordWrap(True)

        mid_btn_layout = QHBoxLayout()
        mid_btn_layout.setSpacing(8)
        self.btn_enable   = QPushButton("ENABLE")
        self.btn_activate = QPushButton("ACTIVATE")
        self.btn_enable.setFixedHeight(32)
        self.btn_activate.setFixedHeight(32)
        mid_btn_layout.addWidget(self.btn_enable)
        mid_btn_layout.addWidget(self.btn_activate)

        self.btn_disable = QPushButton("DISABLE")
        self.btn_disable.setFixedHeight(32)
        self.btn_activate.setStyleSheet("QPushButton { color:#2563eb; border:1px solid #93c5fd; }")
        self.btn_disable.setStyleSheet("QPushButton { color:#dc2626; border:1px solid #fca5a5; background-color:#fef2f2; }")

        control_layout.addWidget(lbl_cp)
        control_layout.addWidget(self.lbl_status_display)
        control_layout.addLayout(mid_btn_layout)
        control_layout.addWidget(self.btn_disable)

        layout.addWidget(control_group)
        layout.addStretch(1)

        # ── [2] View Mode ────────────────────────────────────────
        view_group  = QWidget()
        view_layout = QVBoxLayout(view_group)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(8)

        lbl_view = QLabel("View Mode")
        lbl_view.setFont(header_font)
        lbl_view.setStyleSheet(header_style)

        view_btn_layout = QHBoxLayout()
        view_btn_layout.setSpacing(8)
        for v_name in ["Chart", "Table", "Echo"]:
            btn = QPushButton(v_name)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, name=v_name: self.view_changed.emit(name.lower()))
            view_btn_layout.addWidget(btn)

        view_layout.addWidget(lbl_view)
        view_layout.addLayout(view_btn_layout)

        layout.addWidget(view_group)
        layout.addStretch(1)

        # ── [3] Telemetry Units ──────────────────────────────────
        units_group  = QWidget()
        units_layout = QVBoxLayout(units_group)
        units_layout.setContentsMargins(0, 0, 0, 0)
        units_layout.setSpacing(8)

        lbl_units_title = QLabel("Telemetry Units")
        lbl_units_title.setFont(header_font)
        lbl_units_title.setStyleSheet(header_style)

        lbl_units_content = QLabel()
        lbl_units_content.setTextFormat(Qt.TextFormat.RichText)
        lbl_units_content.setText(_TELEMETRY_HTML)   # 모듈 로드 시 미리 계산된 HTML 재사용
        lbl_units_content.setStyleSheet("""
            color: #374151; font-size: 11px; line-height: 1.6;
            font-family: 'Consolas', monospace;
            padding: 10px; background-color: #ffffff;
            border: 1px solid #e5e7eb; border-radius: 8px;
        """)

        units_layout.addWidget(lbl_units_title)
        units_layout.addWidget(lbl_units_content)

        layout.addWidget(units_group)
        layout.addStretch(1)

        # ── [4] Command Input ────────────────────────────────────
        cmd_group  = QWidget()
        cmd_layout = QVBoxLayout(cmd_group)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_layout.setSpacing(8)

        lbl_cmd = QLabel("Command Input (CMD)")
        lbl_cmd.setFont(header_font)
        lbl_cmd.setStyleSheet(header_style)

        self.cmd_pill = QFrame()
        self.cmd_pill.setFixedHeight(42)
        self.cmd_pill.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 21px; }
            QFrame:hover { border: 1px solid #3b82f6; }
        """)

        pill_layout = QHBoxLayout(self.cmd_pill)
        pill_layout.setContentsMargins(14, 0, 5, 0)
        pill_layout.setSpacing(5)

        self.input_cmd = QLineEdit()
        self.input_cmd.setPlaceholderText("CX,ON  또는  MEC,SERVO,ON")
        self.input_cmd.setStyleSheet("QLineEdit { border: none; background: transparent; font-size: 11px; }")

        self.btn_send = QPushButton("SEND")
        self.btn_send.setFixedSize(56, 32)
        self.btn_send.setStyleSheet("""
            QPushButton { border: none; background-color: #3b82f6; color: white; border-radius: 16px; }
            QPushButton:hover { background-color: #2563eb; }
        """)

        pill_layout.addWidget(self.input_cmd)
        pill_layout.addWidget(self.btn_send)

        cmd_layout.addWidget(lbl_cmd)
        cmd_layout.addWidget(self.cmd_pill)
        layout.addWidget(cmd_group)

        # ── 시그널 배선 ──────────────────────────────────────────
        self.btn_enable.clicked.connect(self.backend.load_sim_data)
        self.btn_activate.clicked.connect(self.backend.activate_sim)
        self.btn_disable.clicked.connect(self.on_disable_click)
        self.input_cmd.returnPressed.connect(self.send_custom_command)
        self.btn_send.clicked.connect(self.send_custom_command)
        self.backend.state_changed.connect(self.update_state_ui)
        self.backend.data_received.connect(self.process_cansat_state)
        self.update_state_ui(self.backend.state)

    # ──────────────────────────────────────────────────────────────
    # 슬롯 메서드
    # ──────────────────────────────────────────────────────────────

    def process_cansat_state(self, data_list):
        if len(data_list) <= 4:
            return
        try:
            current_pkt_num = int(data_list[2])
            if self.last_packet_num != -1:
                diff = current_pkt_num - self.last_packet_num
                if diff > 1:
                    self.lost_packets_count += diff - 1
            self.last_packet_num = current_pkt_num
        except (ValueError, IndexError):
            pass
        self.last_cansat_state = data_list[4]
        self.update_display()

    def update_display(self):
        state        = self.backend.state
        is_connected = self.backend.worker.isRunning()

        mode_text, color_style = (
            _STATE_STYLES.get(state)
            or (_STYLE_CONNECTED if is_connected else _STYLE_IDLE)
        )

        # 스타일이 바뀐 경우에만 setStyleSheet 호출 (매 패킷 재적용 방지)
        full_style = color_style + _STATUS_BASE
        if full_style != self._last_style:
            self.lbl_status_display.setStyleSheet(full_style)
            self._last_style = full_style

        self.lbl_status_display.setText(
            f"STATE MODE: {mode_text}\n"
            f"CURRENT CMD: {self.current_cmd_log}\n"
            f"STATE: {self.last_cansat_state}\n"
            f"LOST PKTS: {self.lost_packets_count}"
        )

    def on_disable_click(self):
        if self.backend.state == SIM_STATE["RUNNING"]:
            self.backend.activate_sim()
        self.backend.update_state(SIM_STATE["IDLE"])
        self.current_cmd_log   = "Reset"
        self.last_cansat_state = "LAUNCH_PAD"
        self.update_display()

    def update_state_ui(self, state):
        is_sim_active = state in (SIM_STATE["LOADED"], SIM_STATE["ENABLED"], SIM_STATE["RUNNING"])
        self.btn_enable.setEnabled(not is_sim_active)
        self.btn_disable.setEnabled(is_sim_active)
        self.btn_activate.setEnabled(is_sim_active and state != SIM_STATE["RUNNING"])
        self.update_display()

    def send_custom_command(self):
        raw_input = self.input_cmd.text().strip().replace(" ", "").upper()
        if not raw_input:
            return

        final_cmd = raw_input if raw_input.startswith("CMD") else f"CMD,{TEAM_ID},{raw_input}"

        if self.backend.worker.isRunning():
            self.backend.worker.send_command(final_cmd)
            self.current_cmd_log = final_cmd
        else:
            self.current_cmd_log = "⚠️ Disconnected"

        self.update_display()
        self.input_cmd.clear()
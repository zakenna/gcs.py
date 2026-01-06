from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QWidget, QHBoxLayout, QLabel, 
                             QPushButton, QSizePolicy, QLineEdit) # QLineEdit 추가
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from src.backend import SIM_STATE
from src.components.map_view import MapWidget

class SidebarWidget(QFrame):
    view_changed = pyqtSignal(str) 

    def __init__(self, backend_ref):
        super().__init__()
        self.backend = backend_ref
        
        # 너비 240px 유지
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
                border-radius: 4px; padding: 0px; font-size: 11px; font-weight: bold;
                border: 1px solid #d1d5db; background-color: white;
            }
            QPushButton:hover { background-color: #f3f4f6; }
            QPushButton:disabled { background-color: #f3f4f6; color: #9ca3af; border: 1px solid #e5e7eb; }
            
            /* CMD 입력창 스타일 */
            QLineEdit {
                border: 1px solid #d1d5db; border-radius: 4px; padding: 6px;
                background-color: white; font-family: monospace;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(12, 20, 12, 20) 

        header_style = "border-bottom: 1px solid #d1d5db; padding-bottom: 4px; margin-bottom: 5px;"
        header_font = QFont("Segoe UI", 10, QFont.Weight.Bold)

        # =========================================================
        # [1] Control Panel
        # =========================================================
        control_group = QWidget()
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(0,0,0,0)
        control_layout.setSpacing(6)
        
        lbl_cp = QLabel("Control Panel")
        lbl_cp.setFont(header_font)
        lbl_cp.setStyleSheet(header_style)
        
        self.lbl_mode_indicator = QLabel("REAL MODE")
        self.lbl_mode_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_mode_indicator.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_mode_indicator.setFixedHeight(30)
        self.lbl_mode_indicator.setStyleSheet("""
            background-color: #dcfce7; color: #15803d; 
            border: 1px solid #86efac; border-radius: 4px;
        """)

        mid_btn_layout = QHBoxLayout()
        mid_btn_layout.setSpacing(6)

        self.btn_enable = QPushButton("📂 Load")     
        self.btn_activate = QPushButton("▶ Start")   
        self.btn_enable.setFixedHeight(30)
        self.btn_activate.setFixedHeight(30)
        self.btn_enable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_activate.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        mid_btn_layout.addWidget(self.btn_enable)
        mid_btn_layout.addWidget(self.btn_activate)

        self.btn_disable = QPushButton("⏹ Disable (Reset)")
        self.btn_disable.setFixedHeight(30) 
        self.btn_disable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.btn_activate.setStyleSheet("color: #2563eb; border: 1px solid #93c5fd;")
        self.btn_disable.setStyleSheet("color: #dc2626; border: 1px solid #fca5a5; background-color: #fef2f2;")

        self.btn_enable.clicked.connect(self.backend.load_sim_data)
        self.btn_activate.clicked.connect(self.backend.activate_sim)
        self.btn_disable.clicked.connect(self.on_disable_click)

        control_layout.addWidget(lbl_cp)
        control_layout.addWidget(self.lbl_mode_indicator)
        control_layout.addLayout(mid_btn_layout)
        control_layout.addWidget(self.btn_disable)
        
        layout.addWidget(control_group)

        # [Status Monitor 삭제됨]

        # =========================================================
        # [2] GPS Tracking (위로 올라옴)
        # =========================================================
        gps_group = QWidget()
        gps_layout = QVBoxLayout(gps_group)
        gps_layout.setContentsMargins(0,0,0,0)
        
        lbl_gps = QLabel("GPS Tracking")
        lbl_gps.setFont(header_font)
        lbl_gps.setStyleSheet(header_style)
        
        self.map_view = MapWidget()
        self.map_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.map_view.setMinimumHeight(200) # 지도 공간 확보

        gps_text_row = QHBoxLayout()
        self.lbl_lat = QLabel("0.00000")
        self.lbl_lng = QLabel("0.00000")
        for l in [self.lbl_lat, self.lbl_lng]:
            l.setStyleSheet("color: #6b7280; font-family: monospace; font-size: 11px; font-weight: bold;")
        
        gps_text_row.addWidget(QLabel("Lat:"))
        gps_text_row.addWidget(self.lbl_lat)
        gps_text_row.addStretch()
        gps_text_row.addWidget(QLabel("Lng:"))
        gps_text_row.addWidget(self.lbl_lng)

        gps_layout.addWidget(lbl_gps)
        gps_layout.addWidget(self.map_view)
        gps_layout.addLayout(gps_text_row)
        layout.addWidget(gps_group) 

        # =========================================================
        # [3] View Switcher (위로 올라옴)
        # =========================================================
        view_group = QWidget()
        view_layout = QVBoxLayout(view_group)
        view_layout.setContentsMargins(0,0,0,0)
        
        lbl_view = QLabel("View Mode")
        lbl_view.setFont(header_font)
        lbl_view.setStyleSheet(header_style)
        view_layout.addWidget(lbl_view)
        
        for v_name in ["Table", "Chart", "Echo"]:
            btn = QPushButton(f"{v_name} View")
            # btn.setFixedHeight(30) # 필요 시 주석 해제
            btn.clicked.connect(lambda checked, name=v_name: self.view_changed.emit(name.lower()))
            view_layout.addWidget(btn)

        layout.addWidget(view_group)

        # =========================================================
        # [4] Command Input (남는 하단 공간 활용)
        # =========================================================
        layout.addStretch(1) # 위쪽 요소들을 밀어내고 빈 공간 확보

        cmd_group = QWidget()
        cmd_layout = QVBoxLayout(cmd_group)
        cmd_layout.setContentsMargins(0,0,0,0)
        cmd_layout.setSpacing(5)

        lbl_cmd = QLabel("Command Input (CMD)")
        lbl_cmd.setFont(header_font)
        lbl_cmd.setStyleSheet(header_style)
        
        # 입력창
        self.input_cmd = QLineEdit()
        self.input_cmd.setPlaceholderText("Type command (e.g. RESET)")
        self.input_cmd.setFixedHeight(30)
        
        # 전송 버튼
        self.btn_send = QPushButton("SEND CMD")
        self.btn_send.setFixedHeight(30)
        self.btn_send.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; border: none; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
        """)
        
        # 엔터키 & 버튼 연결
        self.input_cmd.returnPressed.connect(self.send_custom_command)
        self.btn_send.clicked.connect(self.send_custom_command)

        cmd_layout.addWidget(lbl_cmd)
        cmd_layout.addWidget(self.input_cmd)
        cmd_layout.addWidget(self.btn_send)
        
        layout.addWidget(cmd_group)
        
        # 초기화
        self.backend.state_changed.connect(self.update_state_ui)
        self.update_state_ui(self.backend.state)

    def on_disable_click(self):
        if self.backend.state == SIM_STATE["RUNNING"]:
            self.backend.activate_sim() 
        self.backend.update_state(SIM_STATE["IDLE"]) 

    def update_state_ui(self, state):
        self.lbl_sys_state = QLabel(state) # 임시 참조용 (실제 표시는 Control Panel에서 함)
        
        is_sim_active = (state == SIM_STATE["LOADED"] or state == SIM_STATE["ENABLED"] or state == SIM_STATE["RUNNING"])
        
        if is_sim_active:
            self.lbl_mode_indicator.setText("⚠️ SIMULATION")
            self.lbl_mode_indicator.setStyleSheet("""
                background-color: #fff7ed; color: #c2410c; 
                border: 1px solid #fdba74; border-radius: 4px;
            """)
            self.btn_enable.setEnabled(False)
            self.btn_activate.setEnabled(True)
            self.btn_disable.setEnabled(True)
            
            if state == SIM_STATE["RUNNING"]:
                self.btn_activate.setText("⏸ Pause")
            else:
                self.btn_activate.setText("▶ Start")
        else:
            self.lbl_mode_indicator.setText("📡 REAL MODE")
            self.lbl_mode_indicator.setStyleSheet("""
                background-color: #dcfce7; color: #15803d; 
                border: 1px solid #86efac; border-radius: 4px;
            """)
            self.btn_enable.setEnabled(True)
            self.btn_activate.setEnabled(False)
            self.btn_disable.setEnabled(False)

    def update_gps_data(self):
        """Status Monitor가 없어졌으므로 GPS만 업데이트"""
        gps = self.backend.latest_gps
        self.lbl_lat.setText(f"{gps['lat']:.5f}")
        self.lbl_lng.setText(f"{gps['lng']:.5f}")

    def send_custom_command(self):
        """
        커맨드 입력창 처리
        요구사항 3.1.2 포맷(CMD,1062,...)을 자동으로 맞춰줍니다.
        """
        raw_input = self.input_cmd.text().strip().upper()
        if not raw_input:
            return

        team_id = 1062
        final_cmd = ""

        # 1. 사용자가 이미 전체 포맷(CMD,...)을 다 쳤을 경우 -> 그대로 전송
        if raw_input.startswith("CMD"):
            final_cmd = raw_input

        # 2. 단축 명령어 처리 (사용자 편의성)
        else:
            parts = raw_input.split(',')
            # 콤마로 구분하지 않고 스페이스로 쳤을 경우 대응 (예: "CX ON")
            if len(parts) == 1:
                parts = raw_input.split()

            opcode = parts[0]

            # [CASE 1] CX (Telemetry)
            if opcode == "CX":
                # 입력예: CX ON -> CMD,1062,CX,ON
                param = parts[1] if len(parts) > 1 else "ON"
                final_cmd = f"CMD,{team_id},CX,{param}"

            # [CASE 2] ST (Set Time)
            elif opcode == "ST":
                # 입력예: ST GPS -> CMD,1062,ST,GPS
                # 입력예: ST 13:00:00 -> CMD,1062,ST,13:00:00
                param = parts[1] if len(parts) > 1 else "GPS"
                final_cmd = f"CMD,{team_id},ST,{param}"

            # [CASE 3] SIM (Simulation)
            elif opcode == "SIM":
                # 입력예: SIM ENABLE -> CMD,1062,SIM,ENABLE
                param = parts[1] if len(parts) > 1 else "ENABLE"
                final_cmd = f"CMD,{team_id},SIM,{param}"

            # [CASE 4] SIMP (Simulated Pressure)
            elif opcode == "SIMP":
                # 입력예: SIMP 101325 -> CMD,1062,SIMP,101325
                val = parts[1] if len(parts) > 1 else "101325"
                final_cmd = f"CMD,{team_id},SIMP,{val}"

            # [CASE 5] CAL (Calibrate)
            elif opcode == "CAL":
                # 입력예: CAL -> CMD,1062,CAL
                final_cmd = f"CMD,{team_id},CAL"

            # [CASE 6] MEC (Mechanism) - ★ 경고창 없이 즉시 실행
            elif opcode == "MEC":
                # 입력예: MEC,PARA,ON (콤마 권장) 또는 MEC PARA ON
                # 요구사항: CMD,<ID>,MEC,<DEVICE>,<STATE>
                if len(parts) >= 3:
                    device = parts[1]
                    state = parts[2]
                    final_cmd = f"CMD,{team_id},MEC,{device},{state}"
                else:
                    print("⚠️ MEC Format Error: Use 'MEC DEVICE STATE'")
                    return
            elif opcode == "SIMP":
                val = parts[1] if len(parts) > 1 else "101325"
                self.backend.cmd_simp(val) # <--- [변경] 백엔드 함수 호출!
                return # send_custom_command 맨 밑의 send_command를 중복 실행 안 하도록 리턴

            # 그 외 알 수 없는 명령어는 그냥 보냄 (혹시 모르니)
            else:
                final_cmd = f"CMD,{team_id},{raw_input}"

        # 전송 로직
        if self.backend.worker.isRunning():
            self.backend.worker.send_command(final_cmd)
            # 로그에는 "MANUAL" 태그로 남김
            self.backend.log_command("MANUAL", f"Sent: {final_cmd}")
        else:
            print("⚠️ Not connected to port.")
        
        self.input_cmd.clear()
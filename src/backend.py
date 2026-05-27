import datetime
import csv
import os
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QFileDialog
import serial

# =========================================================
# FSW(Teensy) 규격 및 미션 설정 (수정 금지 규격)
# =========================================================
TEAM_ID       = 1062
_TEAM_ID_STR  = str(TEAM_ID)   # 매 패킷마다 str() 변환 방지
SERIAL_PORT_NAME = "COM4"
BAUDRATE         = 115200
CSV_FILENAME     = "Flight_1062.csv"

SIM_STATE = {
    "IDLE":    "IDLE",
    "LOADED":  "LOADED",
    "ENABLED": "ENABLED",
    "RUNNING": "RUNNING",
}

FLIGHT_STATES = {
    "LAUNCH_PAD", "ASCENT", "APOGEE", "DESCENT",
    "PAYLOAD_RELEASE", "PROBE_RELEASE", "LANDED",
}

CSV_HEADERS = [
    "TEAM_ID", "MISSION_TIME", "PACKET_COUNT", "MODE", "STATE",
    "ALTITUDE", "TEMPERATURE", "PRESSURE", "VOLTAGE", "CURRENT",
    "GYRO_R", "GYRO_P", "GYRO_Y",
    "ACCEL_X", "ACCEL_Y", "ACCEL_Z",
    "GPS_TIME", "GPS_ALTITUDE", "GPS_LATITUDE", "GPS_LONGITUDE", "GPS_SATS",
    "CMD_ECHO",
]


class SerialWorker(QThread):
    data_received     = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)

    def __init__(self, port_name, baudrate):
        super().__init__()
        self.port_name   = port_name
        self.baudrate    = baudrate
        self.serial_port = None
        self.is_running  = False

    def run(self):
        self.is_running = True
        try:
            self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=0.1)
            msg = f"✅ [GCS] XBee 연결 성공! 포트: {self.port_name} (Baudrate: {self.baudrate})"
            print(msg)
            self.connection_status.emit(True, msg)

            while self.is_running:
                if self.serial_port and self.serial_port.in_waiting:
                    try:
                        line = self.serial_port.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            self.data_received.emit(line)
                    except Exception:
                        pass
                self.msleep(5)
        except Exception as e:
            msg = f"⚠️ [GCS] 포트 연결 실패 또는 대기 중 ({e})"
            print(msg)
            self.connection_status.emit(False, msg)

    def send_command(self, command_str):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write((command_str.strip() + "\n").encode("utf-8"))
                print(f"📡 [GCS -> FSW TX] {command_str.strip()}")
            except Exception as e:
                print(f"❌ [GCS TX ERROR] 명령어 전송 실패: {e}")

    def stop(self):
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.wait()


class GCSBackend(QObject):
    data_received = pyqtSignal(list)
    log_received  = pyqtSignal(str, str)
    state_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.state       = SIM_STATE["IDLE"]
        self.packet_count = 0
        self.sim_data    = []
        self.sim_index   = 0

        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.send_next_sim_line)

        self.init_csv_file()

        self.worker = SerialWorker(SERIAL_PORT_NAME, BAUDRATE)
        self.worker.data_received.connect(self.process_raw_data)
        self.worker.connection_status.connect(self.handle_connection_log)
        self.worker.start()

    def init_csv_file(self):
        if not os.path.exists(CSV_FILENAME):
            with open(CSV_FILENAME, mode="w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_HEADERS)

    def save_to_csv(self, data_list):
        try:
            with open(CSV_FILENAME, mode="a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(data_list)
        except Exception as e:
            print(f"❌ [GCS CSV ERROR] 파일 기록 실패: {e}")

    def handle_connection_log(self, success, message):
        self.log_received.emit("SYSTEM" if success else "WARNING", message)

    def process_raw_data(self, line):
        print(f"📥 [FSW -> GCS RX] {line}")

        # 디버그 프레임 차단
        if line.startswith("===") or ("TEST" in line and "," not in line):
            self.log_received.emit("FSW_DEBUG", line)
            return

        parts = [p.strip() for p in line.split(",")]

        if len(parts) >= 21 and parts[0] == _TEAM_ID_STR:
            while len(parts) < 22:
                parts.append("")

            try:
                self.packet_count = int(parts[2])
                if parts[4] in FLIGHT_STATES:
                    self.state_changed.emit(parts[4])
            except (ValueError, IndexError):
                pass

            self.data_received.emit(parts)
            self.save_to_csv(parts)
        elif line:
            self.log_received.emit("FSW_TEXT", line)

    # ── 기본 명령어 ──────────────────────────────────────────────

    def cmd_cx_on(self):
        """CX ON 단독 전송. CAL은 별도 버튼으로 분리 (미션 가이드 준수)"""
        self.worker.send_command(f"CMD,{TEAM_ID},CX,ON")
        self.log_received.emit("CMD", "CX ON 명령 전송 (텔레메트리 스트리밍 시작)")

    def cmd_cx_off(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CX,OFF")
        self.log_received.emit("CMD", "CX OFF 명령 전송 (텔레메트리 중단)")

    def cmd_calibrate(self):
        """발사대 설치 후 수동으로 호출해야 함 (자동 묶음 금지)"""
        self.worker.send_command(f"CMD,{TEAM_ID},CAL")
        self.log_received.emit("CMD", "CAL 명령 전송 (지면 기압 센서 영점 보정)")

    def cmd_set_time(self):
        now_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.worker.send_command(f"CMD,{TEAM_ID},ST,{now_time}")
        self.log_received.emit("CMD", f"ST 명령 전송 (GCS 시간 동기화: {now_time})")

    # ── 확장 명령어 ──────────────────────────────────────────────

    def cmd_test_packet(self):
        self.worker.send_command(f"CMD,{TEAM_ID},TEST")
        self.log_received.emit("CMD", "TEST 명령 전송 (즉시 센서 1회 스캔)")

    def cmd_camera_all_on(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CAMERA,ON")
        self.log_received.emit("CMD", "CAMERA ON 명령 전송")

    def cmd_camera_all_off(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CAMERA,OFF")
        self.log_received.emit("CMD", "CAMERA OFF 명령 전송")

    # ── 시뮬레이션 모드 ──────────────────────────────────────────

    def load_sim_data(self):
        """SIM ENABLE만 전송. CAL은 오염 방지를 위해 포함하지 않음 (미션 가이드 준수)"""
        file_path, _ = QFileDialog.getOpenFileName(None, "Open SIM Data", "", "Text Files (*.txt)")
        if not file_path:
            return

        with open(file_path, "r", encoding="utf-8") as f:
            self.sim_data  = [l.strip() for l in f if l.strip()]
        self.sim_index = 0

        self.worker.send_command(f"CMD,{TEAM_ID},SIM,ENABLE")
        self.update_state(SIM_STATE["ENABLED"])
        self.log_received.emit("SIM", "시뮬레이션 데이터 로드 완료, SIM ENABLE 전송")

    def activate_sim(self):
        if self.state == SIM_STATE["RUNNING"]:
            # RUNNING 중 재클릭 → DISABLE (토글)
            self.sim_timer.stop()
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,DISABLE")
            self.sim_index = 0
            self.update_state(SIM_STATE["ENABLED"])
            self.log_received.emit("SIM", "SIM DISABLE 전송 (수동 중단)")
            return

        if not self.sim_data:
            self.log_received.emit("SIM", "⚠️ 로드된 시뮬 데이터 없음")
            return

        self.worker.send_command(f"CMD,{TEAM_ID},SIM,ACTIVATE")
        self.update_state(SIM_STATE["RUNNING"])
        QTimer.singleShot(200, lambda: self.sim_timer.start(1000))
        self.log_received.emit("SIM", "SIM ACTIVATE 전송, 1초 간격 SIMP 주입 시작")

    def send_next_sim_line(self):
        if self.sim_index < len(self.sim_data):
            self.worker.send_command(f"CMD,{TEAM_ID},SIMP,{self.sim_data[self.sim_index]}")
            self.sim_index += 1
        else:
            # 시뮬 완료 → DISABLE 후 IDLE 복귀, 인덱스 리셋
            self.sim_timer.stop()
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,DISABLE")
            self.sim_index = 0
            self.update_state(SIM_STATE["IDLE"])
            self.log_received.emit("SIM", "시뮬레이션 시나리오 완료, SIM DISABLE 전송")

    def update_state(self, new_state):
        self.state = new_state
        self.state_changed.emit(new_state)
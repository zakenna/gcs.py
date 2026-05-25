import time
import datetime
import csv
import os
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QFileDialog
import serial

# =========================================================
# FSW(Teensy) 규격 및 미션 설정 (수정 금지 규격)
# =========================================================
TEAM_ID = 1062
SERIAL_PORT_NAME = "COM4"  # 4번 포트 고정
BAUDRATE = 9600 
CSV_FILENAME = "Flight_1062.csv"

SIM_STATE = {
    "IDLE": "IDLE", "LOADED": "LOADED", "ENABLED": "ENABLED",
    "RUNNING": "RUNNING"
}

FLIGHT_STATES = [
    "LAUNCH_PAD", "ASCENT", "APOGEE", "DESCENT", 
    "PAYLOAD_RELEASE", "PROBE_RELEASE", "LANDED"
]

CSV_HEADERS = [
    "TEAM_ID", "MISSION_TIME", "PACKET_COUNT", "MODE", "STATE", 
    "ALTITUDE", "TEMPERATURE", "PRESSURE", "VOLTAGE", "CURRENT", 
    "GYRO_R", "GYRO_P", "GYRO_Y", 
    "ACCEL_X", "ACCEL_Y", "ACCEL_Z", 
    "GPS_TIME", "GPS_ALTITUDE", "GPS_LATITUDE", "GPS_LONGITUDE", "GPS_SATS", 
    "CMD_ECHO"
]

class SerialWorker(QThread):
    data_received = pyqtSignal(str) 
    connection_status = pyqtSignal(bool, str)

    def __init__(self, port_name, baudrate):
        super().__init__()
        self.port_name = port_name
        self.baudrate = baudrate
        self.serial_port = None
        self.is_running = False

    def run(self):
        self.is_running = True
        try:
            self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=0.1)
            success_msg = f"✅ [GCS] XBee 연결 성공! 포트: {self.port_name} (Baudrate: {self.baudrate})"
            print(success_msg)
            self.connection_status.emit(True, success_msg)
            
            while self.is_running:
                if self.serial_port and self.serial_port.in_waiting:
                    try:
                        # Teensy 문자열 수신 버퍼 안정성을 위해 양끝 공백 및 \r 문자 완벽 strip
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if line: 
                            self.data_received.emit(line)
                    except: pass
                self.msleep(10)
        except Exception as e:
            fail_msg = f"⚠️ [GCS] 포트 연결 실패 또는 대기 중 ({str(e)})"
            print(fail_msg)
            self.connection_status.emit(False, fail_msg)

    def send_command(self, command_str):
        if self.serial_port and self.serial_port.is_open:
            try:
                # FSW의 readStringUntil('\n') 파서 매칭을 위한 오염 방지 표준 포맷팅 (\n 강제 규격)
                msg = command_str.strip() + "\n"
                self.serial_port.write(msg.encode('utf-8'))
                print(f"📡 [GCS -> FSW TX] {command_str.strip()}") 
            except: pass

    def stop(self):
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.wait()


class GCSBackend(QObject):
    data_received = pyqtSignal(list)
    log_received = pyqtSignal(str, str)
    state_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.state = SIM_STATE["IDLE"]
        self.packet_count = 0
        self.sim_data = []
        self.sim_index = 0
        
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.send_next_sim_line)
        
        self.init_csv_file()
        
        # XBee 워커 스레드 기동
        self.worker = SerialWorker(SERIAL_PORT_NAME, BAUDRATE)
        self.worker.data_received.connect(self.process_raw_data)
        self.worker.connection_status.connect(self.handle_connection_log)
        self.worker.start()

    def init_csv_file(self):
        if not os.path.exists(CSV_FILENAME):
            with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(CSV_HEADERS)

    def save_to_csv(self, data_list):
        try:
            with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(data_list)
        except: pass

    def handle_connection_log(self, success, message):
        if success:
            self.log_received.emit("SYSTEM", message)
        else:
            self.log_received.emit("WARNING", message)
            
    def process_raw_data(self, line):
        """[FSW 수신 데이터 실시간 파싱 및 검증]"""
        print(f"📥 [FSW -> GCS RX] {line}") 
        
        parts = [p.strip() for p in line.split(',')]
        
        # FSW generateTelemetry() 필드 출력 개수 매칭 (22개 컬럼 필터링)
        if len(parts) >= 22 and parts[0] == str(TEAM_ID):
            try:
                self.packet_count = int(parts[2])
            except ValueError:
                pass
            
            self.data_received.emit(parts)
            self.save_to_csv(parts)

    # ====================================================
    # FSW(Teensy) 원본 명령어 프로토콜 100% 매칭 함수셋
    # ====================================================
    def cmd_cx_on(self):
        """Teensy는 기압 보정(CAL) 선행이 필수 조건이므로 GCS 매크로 인터록 처리"""
        # 1단계: 지면 기압 보정 송신
        self.worker.send_command(f"CMD,{TEAM_ID},CAL")
        time.sleep(0.2) # Teensy 시리얼 수신 링버퍼 오버플로우 방지 딜레이
        
        # 2단계: 텔레메트리 루프 구동 시작 송신
        self.worker.send_command(f"CMD,{TEAM_ID},CX,ON")
        self.log_received.emit("CMD", "CAL 및 CX ON 명령 연속 전송 완료 (실시간 파싱 가동)")

    def cmd_cx_off(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CX,OFF")
        self.log_received.emit("CMD", "CX OFF 명령 전송")

    def cmd_calibrate(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CAL")
        self.log_received.emit("CMD", "CAL (지면 기압 보정) 명령 전송")

    def cmd_set_time(self):
        # Teensy executeSTCommand() 내 파싱 포맷 고정 (HH:MM:SS)
        now_utc = datetime.datetime.utcnow().strftime("%H:%M:%S")
        self.worker.send_command(f"CMD,{TEAM_ID},ST,{now_utc}")
        self.log_received.emit("CMD", f"ST 명령 전송 (GCS UTC 동기화: {now_utc})")
        
    def cmd_mec_servo_on(self):
        """Teensy FSW executeMECCommand() 토큰 파싱 요구 조건 매칭:
        cmdParts[3] = "SERVO", cmdParts[4] = "ON" (총 5개 토큰 구조 충족)"""
        self.worker.send_command(f"CMD,{TEAM_ID},MEC,SERVO,ON")
        self.log_received.emit("CMD", "MEC SERVO ON 명령 전송")

    def cmd_mec_servo_off(self):
        """Teensy FSW executeMECCommand() 토큰 파싱 요구 조건 매칭:
        cmdParts[3] = "SERVO", cmdParts[4] = "OFF" (총 5개 토큰 구조 충족)"""
        self.worker.send_command(f"CMD,{TEAM_ID},MEC,SERVO,OFF")
        self.log_received.emit("CMD", "MEC SERVO OFF 명령 전송")

    # ====================================================
    # 시뮬레이션 모드 가동 프로토콜
    # ====================================================
    def load_sim_data(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open SIM Data", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.sim_data = [l.strip() for l in f.readlines() if l.strip()]
            self.sim_index = 0
            
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,ENABLE")
            self.update_state(SIM_STATE["ENABLED"])
            self.log_received.emit("SIM", "시뮬레이션 데이터 파일 로드 및 SIM ENABLE 송신 완료")

    def activate_sim(self):
        if self.sim_data:
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,ACTIVATE")
            self.update_state(SIM_STATE["RUNNING"])
            
            # 1초 주기로 Teensy 내부 executeSIMPCommand()에 기압 데이터를 주입하는 타이머 트리거
            QTimer.singleShot(200, lambda: self.sim_timer.start(1000))
            self.log_received.emit("SIM", "SIM ACTIVATE 전송 및 가상 기압 데이터 1초 주기 송신 시작")

    def send_next_sim_line(self):
        if self.sim_index < len(self.sim_data):
            raw_pressure = self.sim_data[self.sim_index]
            # FSW의 executeSIMPCommand() 데이터 규격 포맷 동기화
            self.worker.send_command(f"CMD,{TEAM_ID},SIMP,{raw_pressure}")
            self.sim_index += 1
        else:
            self.sim_timer.stop()
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,DISABLE")
            self.update_state(SIM_STATE["ENABLED"])
            self.log_received.emit("SIM", "시뮬레이션 시나리오 송신 종료 (SIM DISABLE 전송)")

    def update_state(self, new_state):
        self.state = new_state
        self.state_changed.emit(new_state)
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
BAUDRATE = 115200          # FSW의 XBEE.begin(115200) 속도와 완벽 동기화 (기존 9600에서 수정)
CSV_FILENAME = "Flight_1062.csv"

SIM_STATE = {
    "IDLE": "IDLE", 
    "LOADED": "LOADED", 
    "ENABLED": "ENABLED",
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
            # Teensy 4.1 및 XBee 통신 안정성을 위해 timeout 및 데이터 버퍼 최적화
            self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=0.1)
            success_msg = f"✅ [GCS] XBee 연결 성공! 포트: {self.port_name} (Baudrate: {self.baudrate})"
            print(success_msg)
            self.connection_status.emit(True, success_msg)
            
            while self.is_running:
                if self.serial_port and self.serial_port.in_waiting:
                    try:
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if line: 
                            self.data_received.emit(line)
                    except Exception as e:
                        pass
                self.msleep(5) # 지연 최소화를 위해 5ms로 단축
        except Exception as e:
            fail_msg = f"⚠️ [GCS] 포트 연결 실패 또는 대기 중 ({str(e)})"
            print(fail_msg)
            self.connection_status.emit(False, fail_msg)

    def send_command(self, command_str):
        if self.serial_port and self.serial_port.is_open:
            try:
                # FSW readStringUntil('\n') 파서 충돌 방지를 위한 청정 포맷팅
                msg = command_str.strip() + "\n"
                self.serial_port.write(msg.encode('utf-8'))
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
        
        # XBee 스레드 워커 실행 (Baudrate 115200 매칭)
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
        except Exception as e:
            print(f"❌ [GCS CSV ERROR] 파일 기록 실패: {e}")

    def handle_connection_log(self, success, message):
        if success:
            self.log_received.emit("SYSTEM", message)
        else:
            self.log_received.emit("WARNING", message)
            
    def process_raw_data(self, line):
        """[FSW 데이터 실시간 수신 파싱 및 유효성 엄격 검증]"""
        # 콘솔 가독성 및 데이터 모니터링 출력
        print(f"📥 [FSW -> GCS RX] {line}") 
        
        # 디버그 텍스트 프레임 차단용 예외처리 (ex: "=== TEST PACKET ===" 등)
        if line.startswith("===") or "TEST" in line and not "," in line:
            self.log_received.emit("FSW_DEBUG", line)
            return

        parts = [p.strip() for p in line.split(',')]
        
        # 규격 필터링: 첫 번째 토큰이 TEAM_ID이고 데이터 필드가 최소 21개 이상 채워졌는지 검사
        if len(parts) >= 21 and parts[0] == str(TEAM_ID):
            # CMD_ECHO가 공백인 경우 리스트 크기 유연성을 확보하기 위해 부족분 패딩 처리
            while len(parts) < 22:
                parts.append("")
                
            try:
                self.packet_count = int(parts[2])
                # FSW 상태 파싱 후 변경점 감지 시 로그 발생
                fsw_current_state = parts[4]
                if fsw_current_state in FLIGHT_STATES:
                    self.state_changed.emit(fsw_current_state)
            except ValueError:
                pass
            
            # 메인 GUI 데이터 연동 시그널 발생 및 CSV 영구 저장
            self.data_received.emit(parts)
            self.save_to_csv(parts)
        else:
            # 기타 FSW의 디버깅 Serial.print 문 수신 처리
            if line:
                self.log_received.emit("FSW_TEXT", line)

    # ====================================================
    # FSW(Teensy) 매커니즘 100% 매칭 기본 명령어 컴포넌트
    # ====================================================
    def cmd_cx_on(self):
        """텔레메트리 스트리밍 활성화 및 자동 기압 보정 인터록 매크로"""
        # 1단계: 지면 기압 보정(CAL) 선행 필수 처리
        self.worker.send_command(f"CMD,{TEAM_ID},CAL")
        time.sleep(0.2) # 틴시 링버퍼 오버플로우 차단 방지 가드 타임
        
        # 2단계: 텔레메트리 루프 가동 시작 송신
        self.worker.send_command(f"CMD,{TEAM_ID},CX,ON")
        self.log_received.emit("CMD", "CAL 및 CX ON 명령 연속 전송 완료 (실시간 파싱 가동)")

    def cmd_cx_off(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CX,OFF")
        self.log_received.emit("CMD", "CX OFF (텔레메트리 중단) 명령 전송")

    def cmd_calibrate(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CAL")
        self.log_received.emit("CMD", "CAL (지면 기압 센서 영점 보정) 명령 전송")

    def cmd_set_time(self):
        """Teensy executeSTCommand()에 맞춰 현재 컴퓨터 시간 동기화"""
        now_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.worker.send_command(f"CMD,{TEAM_ID},ST,{now_time}")
        self.log_received.emit("CMD", f"ST 명령 전송 (GCS 시간 동기화: {now_time})")

    # ====================================================
    # FSW 전용 추가 테스트 및 확장 조작 명령어 셋 (신규 추가)
    # ====================================================
    def cmd_test_packet(self):
        """CMD,1062,TEST -> 정기 송신 외에 즉시 모든 센서 데이터를 1회 강제 요청"""
        self.worker.send_command(f"CMD,{TEAM_ID},TEST")
        self.log_received.emit("CMD", "TEST (즉시 센서 1회 스캔 및 패킷 출력) 명령 전송")

    def cmd_camera_all_on(self):
        """CMD,1062,CAMERA,ON -> 페이로드 및 그라운드 카메라 동시 녹화 강제 시작"""
        self.worker.send_command(f"CMD,{TEAM_ID},CAMERA,ON")
        self.log_received.emit("CMD", "CAMERA ON (듀얼 카메라 동시 녹화 시작) 명령 전송")

    def cmd_camera_all_off(self):
        """CMD,1062,CAMERA,OFF -> 듀얼 카메라 동시 녹화 강제 종료"""
        self.worker.send_command(f"CMD,{TEAM_ID},CAMERA,OFF")
        self.log_received.emit("CMD", "CAMERA OFF (듀얼 카메라 동시 녹화 종료) 명령 전송")

    def cmd_servo_test_on(self):
        """CMD,1062,SERVO,ON -> 수동 모터 구동 테스트 명령 (자율 조향 중엔 FSW에서 차단됨)"""
        self.worker.send_command(f"CMD,{TEAM_ID},SERVO,ON")
        self.log_received.emit("CMD", "SERVO 수동 구동(ON) 명령 전송")

    def cmd_servo_test_off(self):
        """CMD,1062,SERVO,OFF -> 수동 모터 정지 및 원위치 복귀 명령"""
        self.worker.send_command(f"CMD,{TEAM_ID},SERVO,OFF")
        self.log_received.emit("CMD", "SERVO 수동 원위치 복귀(OFF) 명령 전송")

    def cmd_burn_payload(self):
        """CMD,1062,BURN,PAYLOAD -> 13번 핀 페이로드 분리 번와이어 강제 점화 (2초 비블로킹)"""
        self.worker.send_command(f"CMD,{TEAM_ID},BURN,PAYLOAD")
        self.log_received.emit("CMD", "⚠️ BURN PAYLOAD (13번 핀 페이로드 전분해선 점화) 명령 전송")

    def cmd_burn_probe(self):
        """CMD,1062,BURN,PROBE -> 26번 핀 에그 캔 프로브 분리 번와이어 강제 점화 (2초 비블로킹)"""
        self.worker.send_command(f"CMD,{TEAM_ID},BURN,PROBE")
        self.log_received.emit("CMD", "⚠️ BURN PROBE (26번 핀 계란 분리 전분해선 점화) 명령 전송")

    def cmd_mec_device_ctrl(self, device_name, is_on):
        """
        FSW executeMECCommand()의 토큰 파싱 요구 조건 매칭 매크로 함수
        device_name 입력 범위: "SERVO", "CAM_PL", "CAM_GND"
        """
        status_str = "ON" if is_on else "OFF"
        self.worker.send_command(f"CMD,{TEAM_ID},MEC,{device_name},{status_str}")
        self.log_received.emit("CMD", f"MEC 장치 제어 송신: {device_name} -> {status_str}")

    # ====================================================
    # 시뮬레이션 모드(Simulation Mode) 가동 프로토콜 가드
    # ====================================================
    def load_sim_data(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open SIM Data", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.sim_data = [l.strip() for l in f.readlines() if l.strip()]
            self.sim_index = 0
            
            # FSW 시뮬레이션 활성화
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,ENABLE")
            time.sleep(0.1)
            # SIM 보정 가드 추가 (FSW 내부의 영점 및 기압 연산 정상화 목적)
            self.worker.send_command(f"CMD,{TEAM_ID},CAL")
            
            self.update_state(SIM_STATE["ENABLED"])
            self.log_received.emit("SIM", "시뮬레이션 데이터 로드, SIM ENABLE 및 영점 보정 송신 완료")

    def activate_sim(self):
        if self.sim_data:
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,ACTIVATE")
            self.update_state(SIM_STATE["RUNNING"])
            
            # FSW 타임라인 스케줄러(20ms 루프) 고려하여 대기 후 1초 간격 데이터 주입 트리거
            QTimer.singleShot(200, lambda: self.sim_timer.start(1000))
            self.log_received.emit("SIM", "SIM ACTIVATE 성공 및 가상 기압 패킷 1000ms 주기 동기화")

    def send_next_sim_line(self):
        if self.sim_index < len(self.sim_data):
            raw_pressure = self.sim_data[self.sim_index]
            # FSW의 executeSIMPCommand() 문자열 스캔 포맷 동기화
            self.worker.send_command(f"CMD,{TEAM_ID},SIMP,{raw_pressure}")
            self.sim_index += 1
        else:
            self.sim_timer.stop()
            self.worker.send_command(f"CMD,{TEAM_ID},SIM,DISABLE")
            self.update_state(SIM_STATE["ENABLED"])
            self.log_received.emit("SIM", "시뮬레이션 시나리오 종료 완료 (SIM DISABLE 송신)")

    def update_state(self, new_state):
        self.state = new_state
        self.state_changed.emit(new_state)
import time
import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import serial
import serial.tools.list_ports

# ========================================================
# [설정] 팀 ID와 포트 (가상 포트 프로그램 설정과 일치해야 함)
# ========================================================
TEAM_ID = 1062
SERIAL_PORT_NAME = "COM45" # 지상국 포트 (사용자 환경에 맞게 COM8/COM45 등 수정)
BAUDRATE = 115200

SIM_STATE = {
    "IDLE": "IDLE", "LOADED": "LOADED", "ENABLED": "ENABLED",
    "RUNNING": "RUNNING", "X": "DISABLE"
}

class SerialWorker(QThread):
    data_received = pyqtSignal(str) 

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
            print(f"✅ [GCS] 포트 연결 성공: {self.port_name}")
            
            while self.is_running:
                if self.serial_port.in_waiting:
                    try:
                        # 데이터 읽기
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.data_received.emit(line)
                    except Exception as e:
                        print(f"Read Error: {e}")
                
                self.msleep(10)

        except Exception as e:
            print(f"❌ [GCS] 포트 연결 실패: {e}\n(가상 포트 프로그램이 켜져 있는지 확인하세요!)")
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    def send_command(self, command_str):
        if self.serial_port and self.serial_port.is_open:
            try:
                msg = command_str.strip() + "\n"
                self.serial_port.write(msg.encode('utf-8'))
                print(f"🚀 [GCS 전송]: {msg.strip()}")
            except Exception as e:
                print(f"Send Error: {e}")

    def stop(self):
        self.is_running = False
        self.wait()

class SimDataManager:
    def load_data(self): return True

class GCSBackend(QObject):
    data_received = pyqtSignal(list)
    log_received = pyqtSignal(str)
    state_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.state = SIM_STATE["IDLE"]
        self.packet_count = 0
        self.latest_gps = {"lat": 0.0, "lng": 0.0}
        
        self.worker = SerialWorker(SERIAL_PORT_NAME, BAUDRATE)
        self.worker.data_received.connect(self.process_raw_data)
        self.worker.start()

        self.sim_manager = SimDataManager()
        
    def process_raw_data(self, line):
        parts = line.split(',')
        
        # [데이터 패킷 조건] TEAM_ID로 시작하는지 확인
        if len(parts) > 5 and parts[0] == str(TEAM_ID):
            try:
                self.packet_count = int(parts[2])
                
                # [수정됨] GPS 인덱스 오류 수정 (Sender.py 기준)
                # Sender: Time(16), Lat(17), Lng(18), Sat(19)
                self.latest_gps['lat'] = float(parts[17]) 
                self.latest_gps['lng'] = float(parts[18])
            except:
                pass

            # UI로 데이터 쏘기
            self.data_received.emit(parts)
            
            if "MEC_ON" in parts[-1]:
                self.log_received.emit(f"🔥 MEC ACTIVATED (Packet #{self.packet_count})")
        
        else:
            # 데이터 형식이 아니면 로그창(Echo)에라도 띄움
            self.log_received.emit(f"{line}")

    # ▼▼▼▼▼ [누락되었던 함수 추가] ▼▼▼▼▼
    def log_command(self, tag, msg):
        """명령어 전송 로그를 UI Echo창에 띄우는 함수"""
        self.log_received.emit(f"[{tag}] {msg}")
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    def update_state(self, new_state):
        self.state = new_state
        self.state_changed.emit(new_state)

    # === 명령어 함수들 ===
    def cmd_cx_on(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CX,ON")
        self.log_command("CMD", "CX ON Sent")

    def cmd_cx_off(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CX,OFF")
        self.log_command("CMD", "CX OFF Sent")

    def cmd_calibrate(self):
        self.worker.send_command(f"CMD,{TEAM_ID},CAL")
        self.log_command("CMD", "CAL Sent")

    def cmd_set_time(self):
        now_utc = datetime.datetime.utcnow().strftime("%H:%M:%S")
        self.worker.send_command(f"CMD,{TEAM_ID},ST,{now_utc}")
        self.log_command("CMD", f"Set Time: {now_utc}")
        
    def cmd_mec_on(self):
        self.worker.send_command(f"CMD,{TEAM_ID},MEC,RELEASE,ON")
        self.log_command("CMD", "MEC ON Sent")

    def cmd_simp(self, pressure_val):
        val = str(pressure_val).strip()
        self.worker.send_command(f"CMD,{TEAM_ID},SIMP,{val}")
        self.log_command("SIM", f"Sim Pressure: {val} Pa")

    def load_sim_data(self):
        self.worker.send_command(f"CMD,{TEAM_ID},SIM,ENABLE")
        self.log_command("SIM", "Enable Sent") # 여기가 에러나던 곳
        self.update_state(SIM_STATE["ENABLED"])

    def activate_sim(self):
        self.worker.send_command(f"CMD,{TEAM_ID},SIM,ACTIVATE")
        self.log_command("SIM", "Activate Sent")
        self.update_state(SIM_STATE["RUNNING"])
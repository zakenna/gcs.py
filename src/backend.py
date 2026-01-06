import time
import datetime
import csv
import os
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import serial
import serial.tools.list_ports

TEAM_ID = 1062
SERIAL_PORT_NAME = "COM45" 
BAUDRATE = 115200
CSV_FILENAME = "Flight_1062.csv"

SIM_STATE = {
    "IDLE": "IDLE", "LOADED": "LOADED", "ENABLED": "ENABLED",
    "RUNNING": "RUNNING", "X": "DISABLE"
}

# [수정] 요구사항에 맞춘 CSV 헤더 (Table View와 동일)
CSV_HEADERS = [
    "TEAM_ID", "MISSION_TIME", "PACKET_COUNT", "MODE", "STATE", "ALTITUDE",
    "TEMPERATURE", "PRESSURE", "VOLTAGE", "CURRENT", "GYRO_R", "GYRO_P",
    "GYRO_Y", "ACCEL_R", "ACCEL_P", "ACCEL_Y", "GPS_TIME", "GPS_ALTITUDE",
    "GPS_LATITUDE", "GPS_LONGITUDE", "GPS_SATS", "CMD_ECHO"
]

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
                print(f"[GCS 전송]: {msg.strip()}")
            except Exception as e:
                print(f"Send Error: {e}")

    def stop(self):
        self.is_running = False
        self.wait()

class SimDataManager:
    def load_data(self): return True

class GCSBackend(QObject):
    data_received = pyqtSignal(list)
    log_received = pyqtSignal(str, str)
    state_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.state = SIM_STATE["IDLE"]
        self.packet_count = 0
        self.latest_gps = {"lat": 0.0, "lng": 0.0}
        
        self.init_csv_file()

        self.worker = SerialWorker(SERIAL_PORT_NAME, BAUDRATE)
        self.worker.data_received.connect(self.process_raw_data)
        self.worker.start()

        self.sim_manager = SimDataManager()

    def init_csv_file(self):
        if not os.path.exists(CSV_FILENAME):
            try:
                with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_HEADERS)
                print(f"CSV파일 생성 완료: {CSV_FILENAME}")
            except Exception as e:
                print(f"CSV파일 생성 실패: {e}")

    def save_to_csv(self, data_list):
        try:
            with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(data_list)
        except Exception as e:
            print(f"CSV저장 실패: {e}")
        
    def process_raw_data(self, line):
        parts = line.split(',')
        if len(parts) > 5 and parts[0] == str(TEAM_ID):
            try:
                self.packet_count = int(parts[2])
                self.latest_gps['lat'] = float(parts[18]) 
                self.latest_gps['lng'] = float(parts[19])
            except:
                pass

            self.data_received.emit(parts)
            self.save_to_csv(parts)
            
            if len(parts) > 20 and ("MEC_ON" in parts[-1] or "MEC_ACTIVATED" in parts[-1]):
                self.log_received.emit("SYS", f"🔥 MEC ACTIVATED (Packet #{self.packet_count})")
        else:
            self.log_received.emit("RX", f"{line}")

    def log_command(self, tag, msg):
        self.log_received.emit(tag, msg)

    def update_state(self, new_state):
        self.state = new_state
        self.state_changed.emit(new_state)

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
        self.log_command("SIM", "Enable Sent")
        self.update_state(SIM_STATE["ENABLED"])

    def activate_sim(self):
        self.worker.send_command(f"CMD,{TEAM_ID},SIM,ACTIVATE")
        self.log_command("SIM", "Activate Sent")
        self.update_state(SIM_STATE["RUNNING"])
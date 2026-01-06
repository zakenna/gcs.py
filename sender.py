import sys
import time
import serial
from datetime import datetime

# ========================================================
# [설정] 포트 확인: GCS(COM45)와 연결된 쌍(COM46 등)
# ========================================================
PORT = "COM46"
BAUDRATE = 115200
TEAM_ID = 1062

# [수정] 요구사항 5. STATE 규격 명칭 정의
STATE_LAUNCH_PAD = "LAUNCH_PAD"
STATE_ASCENT = "ASCENT"
STATE_APOGEE = "APOGEE"
STATE_DESCENT = "DESCENT"
STATE_PAYLOAD_RELEASE = "PAYLOAD_RELEASE"
STATE_LANDED = "LANDED"

class VirtualSatellite:
    def __init__(self):
        self.packet_count = 0
        self.mode = "F" # Requirement 4: 'F' or 'S'
        
        # 초기 상태는 LAUNCH_PAD (Requirement 5)
        self.state = STATE_LAUNCH_PAD
        self.mec_activated = False
        
        self.pressure = 101325.0 # 내부 계산용 Pa 단위 유지
        self.altitude = 0.0      
        self.max_altitude = 0.0
        
        self.last_command_code = "None"

        try:
            self.ser = serial.Serial(PORT, BAUDRATE, timeout=0.1)
            print(f"✅ [위성] 실행됨: {PORT} (대기중...)")
        except Exception as e:
            print(f"❌ 포트 열기 실패: {e}")
            sys.exit(1)

        self.is_sending = False 
        self.last_send_time = 0 

    def calculate_altitude(self, pressure):
        # 고도 계산 (Pa 단위 사용)
        return 44330.0 * (1.0 - (pressure / 101325.0)**(1/5.255))

    def update_flight_logic(self):
        self.altitude = self.calculate_altitude(self.pressure)
        if self.altitude > self.max_altitude:
            self.max_altitude = self.altitude

        # 상태 천이 로직 (시뮬레이션)
        if self.state == STATE_LAUNCH_PAD:
            if self.altitude > 50:
                self.state = STATE_ASCENT
                print(f"🚀 상승 감지! -> {self.state}")

        elif self.state == STATE_ASCENT:
            # 정점 도달 시뮬레이션 (간략화)
            if self.max_altitude - self.altitude > 10: 
                self.state = STATE_DESCENT # 실제론 APOGEE 등을 거칠 수 있음
                self.trigger_mec_on("AUTO_APOGEE")

        elif self.state == STATE_DESCENT:
            if self.altitude < 10:
                self.state = STATE_LANDED
                print(f"🛬 착륙! -> {self.state}")

    def trigger_mec_on(self, source):
        if not self.mec_activated:
            self.mec_activated = True
            print(f"\n🔥🔥🔥 [MEC ACTIVATED] ({source}) 🔥🔥🔥\n")

    def process_command(self, cmd_line):
        cmd_line = cmd_line.strip()
        if not cmd_line: return

        print(f"📩 [수신됨] {cmd_line}")
        # Requirement 18: CMD_ECHO에는 콤마가 없어야 함
        self.last_command_code = cmd_line.replace(',', '')

        parts = cmd_line.split(',')
        if len(parts) < 3 or parts[0] != "CMD":
            return

        opcode = parts[2]

        if opcode == "CX":
            param = parts[3] if len(parts) > 3 else "OFF"
            if param == "ON":
                self.is_sending = True
                print("✅ Telemetry ON")
            else:
                self.is_sending = False
                print("🛑 Telemetry OFF")
        
        elif opcode == "SIM":
            # SIM,ENABLE 또는 SIM,ACTIVATE 수신 시 Simulation Mode로 전환
            self.mode = "S"
            print("👾 [SIM] Simulation Mode Activated (S)")

        elif opcode == "SIMP":
            try:
                self.pressure = float(parts[3])
                self.mode = "S" # Requirement 4
                print(f"📉 기압 변경: {self.pressure} Pa")
            except:
                pass

        elif opcode == "MEC":
            self.trigger_mec_on("GCS_MANUAL")

        elif opcode == "CAL":
            self.altitude = 0
            self.max_altitude = 0
            self.state = STATE_LAUNCH_PAD # 리셋 시 LAUNCH_PAD로 복귀
            self.mec_activated = False
            self.pressure = 101325.0
            self.last_command_code = "CAL"
            print("🔄 리셋 (CAL)")

    def run(self):
        while True:
            if self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8', errors='ignore')
                    self.process_command(line)
                except Exception as e:
                    print(f"Error reading: {e}")

            self.update_flight_logic()

            current_time = time.time()
            if self.is_sending and (current_time - self.last_send_time >= 1.0):
                # Requirement 2, 13: UTC Time (hh:mm:ss)
                curr_time_str = datetime.utcnow().strftime("%H:%M:%S")
                
                self.packet_count += 1 # Requirement 3
                
                # [데이터 패킷 생성 - 총 22개 필드]
                # 1. TEAM_ID (1062)
                # 2. MISSION_TIME
                # 3. PACKET_COUNT
                # 4. MODE (F or S)
                # 5. STATE (LAUNCH_PAD, ASCENT, etc.)
                packet = f"{TEAM_ID},{curr_time_str},{self.packet_count},{self.mode},{self.state},"
                
                # 6. ALTITUDE (0.1m resolution)
                # 7. TEMPERATURE (0.1C)
                # 8. PRESSURE (kPa, 0.1 resolution) -> 101325 Pa / 1000 = 101.3 kPa
                pressure_kpa = self.pressure / 1000.0
                # 9. VOLTAGE (0.1V)
                # 10. CURRENT (0.01A) -> 0.50A 예시
                packet += f"{self.altitude:.1f},25.0,{pressure_kpa:.1f},12.0,0.50," 
                
                # 11. GYRO R, P, Y (deg/s)
                # 12. ACCEL R, P, Y (deg/s^2) - Requirement text follows
                packet += "0.0,0.0,0.0,0.1,0.1,9.8," 
                
                # 13. GPS_TIME (UTC)
                # 14. GPS_ALTITUDE (0.1m)
                # 15. GPS_LATITUDE (0.0001 deg)
                # 16. GPS_LONGITUDE (0.0001 deg)
                # 17. GPS_SATS (Integer)
                packet += f"{curr_time_str},0.0,37.5412,127.0123,5," 
                
                # 18. CMD_ECHO (Last command text, no commas)
                packet += f"{self.last_command_code}"
                
                self.ser.write((packet + "\n").encode('utf-8'))
                print(f"🚀 [TX] #{self.packet_count} | State: {self.state} | Pres: {pressure_kpa:.1f} kPa")
                
                self.last_send_time = current_time 

            time.sleep(0.01)

if __name__ == "__main__":
    sat = VirtualSatellite()
    sat.run()
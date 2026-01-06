import sys
import time
import serial

# ========================================================
# [중요] GCS(COM8)와 짝인 포트로 설정 (COM9 등)
# ========================================================
PORT = "COM46"
BAUDRATE = 115200
TEAM_ID = 1062

# 상태 상수
STATE_IDLE = "IDLE"
STATE_ASCENT = "ASCENT"
STATE_DESCENT = "DESCENT"
STATE_LANDED = "LANDED"

class VirtualSatellite:
    def __init__(self):
        self.mission_time = 0
        self.packet_count = 0
        self.mode = "F"
        self.state = STATE_IDLE
        self.mec_activated = False
        
        self.pressure = 101325.0 
        self.altitude = 0.0      
        self.max_altitude = 0.0

        # 시리얼 연결
        try:
            self.ser = serial.Serial(PORT, BAUDRATE, timeout=0.1) # 타임아웃을 짧게!
            print(f"✅ [위성] 실행됨: {PORT} (명령 대기중...)")
        except Exception as e:
            print(f"❌ 포트 열기 실패: {e}")
            sys.exit(1)

        self.is_sending = False 
        self.last_send_time = 0 # 마지막 전송 시간 기록용

    def calculate_altitude(self, pressure):
        return 44330.0 * (1.0 - (pressure / 101325.0)**(1/5.255))

    def update_flight_logic(self):
        self.altitude = self.calculate_altitude(self.pressure)
        if self.altitude > self.max_altitude:
            self.max_altitude = self.altitude

        if self.state == STATE_IDLE:
            if self.altitude > 50:
                self.state = STATE_ASCENT
                print(f"🚀 [AUTO] 상승 감지 (Alt: {self.altitude:.1f}m)")

        elif self.state == STATE_ASCENT:
            if self.max_altitude - self.altitude > 20:
                self.state = STATE_DESCENT
                self.trigger_mec_on("AUTO_APOGEE")

        elif self.state == STATE_DESCENT:
            if self.altitude < 10:
                self.state = STATE_LANDED
                print(f"🛬 [AUTO] 착륙 감지")

    def trigger_mec_on(self, source):
        if not self.mec_activated:
            self.mec_activated = True
            print(f"\n🔥🔥🔥 [MEC ACTIVATED] ({source}) 🔥🔥🔥\n")

    def process_command(self, cmd_line):
        """명령어 처리 및 디버깅 출력"""
        cmd_line = cmd_line.strip()
        if not cmd_line: return

        print(f"📩 [수신됨] {cmd_line}") # <-- 여기가 핵심! 신호 오는지 확인

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

        elif opcode == "SIMP":
            try:
                self.pressure = float(parts[3])
                self.mode = "S"
                print(f"📉 기압 변경: {self.pressure} Pa")
            except:
                pass

        elif opcode == "MEC":
            self.trigger_mec_on("GCS_MANUAL")

        elif opcode == "CAL":
            self.altitude = 0
            self.max_altitude = 0
            self.state = STATE_IDLE
            self.mec_activated = False
            self.pressure = 101325.0
            print("🔄 리셋 (CAL)")

    def run(self):
        while True:
            # 1. 명령어 확인 (매우 빠르게 반복)
            if self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8', errors='ignore')
                    self.process_command(line)
                except Exception as e:
                    print(f"Error reading: {e}")

            # 2. 자율 비행 로직 (항상 실행)
            self.update_flight_logic()

            # 3. 데이터 전송 (1초에 한 번만 실행)
            current_time = time.time()
            if self.is_sending and (current_time - self.last_send_time >= 1.0):
                self.mission_time += 1
                self.packet_count += 1
                
                packet = f"{TEAM_ID},{self.mission_time},{self.packet_count},{self.mode},{self.state},"
                packet += f"{self.altitude:.1f},25.0,1013.2,12.0,0.5," 
                packet += "0.0,0.0,0.0,0.1,0.1,9.8," 
                packet += "12:00:00,37.5,127.0,5," 
                packet += "MEC_ON" if self.mec_activated else "None"
                
                self.ser.write((packet + "\n").encode('utf-8'))
                print(f"🚀 [TX] Packet #{self.packet_count}") # 로그 간소화
                
                self.last_send_time = current_time # 마지막 전송 시간 갱신

            # 4. 아주 짧은 대기 (CPU 과부하 방지용, 0.01초)
            # 명령어 수신을 방해하지 않을 정도로 짧게 잡음
            time.sleep(0.01)

if __name__ == "__main__":
    sat = VirtualSatellite()
    sat.run()
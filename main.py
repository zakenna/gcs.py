import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 우리가 만든 모듈 불러오기 (src 폴더의 main_window.py)
from src.main_window import MainWindow

def main():
    # 1. 고해상도(High DPI) 모니터 대응 설정
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 2. 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 3. 전역 폰트 설정 (Segoe UI, 10pt)
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    
    # 4. 메인 윈도우 생성 및 표시
    # MainWindow 내부에서 Backend와 UI 컴포넌트들이 자동으로 연결됩니다.
    window = MainWindow()
    window.show()
    
    # 5. 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
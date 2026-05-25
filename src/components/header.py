import os
import datetime
from PyQt6.QtWidgets import (QFrame, QGridLayout, QWidget, QHBoxLayout, QLabel, 
                             QVBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor

class HeaderWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(96)
        
        # 테마 상태 저장 변수 (False: Dark, True: Light)
        self.is_light_theme = False
        
        # 초기 테마 설정
        self.apply_theme()

        layout = QGridLayout(self)
        layout.setContentsMargins(40, 0, 40, 0)
        layout.setSpacing(0)

        # =========================================================
        # [1] Left Section: 로고 + GCS Title
        # =========================================================
        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(64, 64)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # ★ 클릭 가능하도록 설정 및 이벤트 필터 등록
        self.logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logo_label.installEventFilter(self) # 이벤트를 이 클래스에서 감시

        image_path = "assets/CosmoLink.png"
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
            
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 150))
            shadow.setOffset(0, 0)
            self.logo_label.setGraphicsEffect(shadow)
        else:
            self.logo_label.setText("LOGO")
            self.logo_label.setStyleSheet("border: 1px dashed #6b7280; color: #9ca3af;")

        text_group = QWidget()
        text_layout = QVBoxLayout(text_group)
        text_layout.setContentsMargins(0, 12, 0, 12)
        text_layout.setSpacing(0)
        
        self.lbl_gcs = QLabel("GCS") # 인스턴스 변수로 변경 (색상 제어용)
        self.lbl_gcs.setFont(QFont("Segoe UI", 24, QFont.Weight.ExtraBold))
        
        self.lbl_team = QLabel("Team ID: 1062") # 인스턴스 변수로 변경
        self.lbl_team.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))

        text_layout.addWidget(self.lbl_gcs)
        text_layout.addWidget(self.lbl_team)

        left_layout.addWidget(self.logo_label)
        left_layout.addWidget(text_group)
        left_layout.addStretch()

        # =========================================================
        # [2] Center Section: Main Title
        # =========================================================
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_title = QLabel("CosmoLink") # 인스턴스 변수로 변경
        self.lbl_title.setFont(QFont("Segoe UI", 25, QFont.Weight.DemiBold))
        
        title_layout.addWidget(self.lbl_title)

        # =========================================================
        # [3] Right Section: Time & Packets
        # =========================================================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container) 
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_layout.setSpacing(2)

        self.time_label = QLabel("00:00:00 UTC")
        self.time_label.setFont(QFont("Courier New", 18, QFont.Weight.Bold)) 
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.packet_label = QLabel("PACKETS: 0")
        self.packet_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.packet_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        right_layout.addWidget(self.time_label)
        right_layout.addWidget(self.packet_label)

        layout.addWidget(left_container, 0, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title_container, 0, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(right_container, 0, 0, Qt.AlignmentFlag.AlignRight)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    # ★ 테마 적용 함수
    def apply_theme(self):
        """is_light_theme 값에 따라 스타일 시트를 일괄 적용"""
        if self.is_light_theme:
            # 밝은 회색 테마
            self.setStyleSheet("""
                HeaderWidget { background-color: #f3f4f6; border-bottom: 1px solid #d1d5db; }
                HeaderWidget QWidget { background-color: transparent; }
                QLabel { color: #111827; }
            """)
            if hasattr(self, 'time_label'): self.time_label.setStyleSheet("color: #16a34a;") # 짙은 녹색
            if hasattr(self, 'packet_label'): self.packet_label.setStyleSheet("color: #2563eb;") # 짙은 파란색
            if hasattr(self, 'lbl_team'): self.lbl_team.setStyleSheet("color: #6b7280;")
        else:
            # 기존 어두운 테마
            self.setStyleSheet("""
                HeaderWidget {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                      stop:0 #111827, stop:0.5 #1f2937, stop:1 #111827);
                    border-bottom: 1px solid #374151;
                }
                HeaderWidget QWidget { background-color: transparent; }
                QLabel { color: #f3f4f6; }
            """)
            if hasattr(self, 'time_label'): self.time_label.setStyleSheet("color: #4ade80;")
            if hasattr(self, 'packet_label'): self.packet_label.setStyleSheet("color: #60a5fa;")
            if hasattr(self, 'lbl_team'): self.lbl_team.setStyleSheet("color: #9ca3af;")

    # ★ 이벤트 필터: 로고 클릭 감지
    def eventFilter(self, obj, event):
        if obj == self.logo_label and event.type() == event.Type.MouseButtonPress:
            self.is_light_theme = not self.is_light_theme # 상태 토글
            self.apply_theme()
            return True
        return super().eventFilter(obj, event)

    def update_time(self):
        now = datetime.datetime.utcnow().strftime("%H:%M:%S UTC")
        self.time_label.setText(now)

    def update_packet_count(self, count):
        self.packet_label.setText(f"PACKETS: {count}")
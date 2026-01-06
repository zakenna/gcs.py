import os
import datetime
from PyQt6.QtWidgets import (QFrame, QGridLayout, QWidget, QHBoxLayout, QLabel, 
                             QVBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor

class HeaderWidget(QFrame):
    def __init__(self):
        super().__init__()
        # 헤더 높이 설정 (충분한 공간 확보)
        self.setFixedHeight(96)
        
        # 스타일시트: 어두운 그라데이션 배경
        self.setStyleSheet("""
            HeaderWidget {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                  stop:0 #111827, stop:0.5 #1f2937, stop:1 #111827);
                border-bottom: 1px solid #374151;
            }
            HeaderWidget QWidget { background-color: transparent; }
            QLabel { color: #f3f4f6; font-family: 'Segoe UI', 'Arial', sans-serif; }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(40, 0, 40, 0) # 좌우 여백
        layout.setSpacing(0)

        # =========================================================
        # [1] Left Section: 로고 + GCS Title
        # =========================================================
        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)

        # 로고 이미지 설정
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(64, 64)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        image_path = "assets/CosmoLink.webp"
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
            
            # 그림자 효과
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 150))
            shadow.setOffset(0, 0)
            self.logo_label.setGraphicsEffect(shadow)
        else:
            # 이미지가 없을 경우 텍스트로 대체
            self.logo_label.setText("LOGO")
            self.logo_label.setStyleSheet("border: 1px dashed #6b7280; color: #9ca3af;")

        # 텍스트 그룹 (GCS / Team ID)
        text_group = QWidget()
        text_layout = QVBoxLayout(text_group)
        text_layout.setContentsMargins(0, 12, 0, 12)
        text_layout.setSpacing(0)
        
        lbl_gcs = QLabel("GCS")
        lbl_gcs.setFont(QFont("Segoe UI", 24, QFont.Weight.ExtraBold))
        
        lbl_team = QLabel("Team ID: 1062")
        lbl_team.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        lbl_team.setStyleSheet("color: #9ca3af;") 

        text_layout.addWidget(lbl_gcs)
        text_layout.addWidget(lbl_team)

        left_layout.addWidget(self.logo_label)
        left_layout.addWidget(text_group)
        left_layout.addStretch()

        # =========================================================
        # [2] Center Section: Main Title
        # =========================================================
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("Team CosmoLink")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        lbl_title.setStyleSheet("color: #e5e7eb; letter-spacing: 1px;")
        
        title_layout.addWidget(lbl_title)

        # =========================================================
        # [3] Right Section: Time & Packets
        # =========================================================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container) 
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_layout.setSpacing(2) # 시간과 패킷 사이 간격 좁게

        # 1. 시간 라벨 (위쪽 배치)
        self.time_label = QLabel("00:00:00 UTC")
        self.time_label.setFont(QFont("Courier New", 18, QFont.Weight.Bold)) 
        self.time_label.setStyleSheet("color: #4ade80;") # 밝은 녹색
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # 2. 패킷 카운트 라벨 (아래쪽 배치)
        self.packet_label = QLabel("PACKETS: 0")
        self.packet_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.packet_label.setStyleSheet("color: #60a5fa; letter-spacing: 1px;") # 밝은 파란색
        self.packet_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # 레이아웃에 추가 (순서: 시간 -> 패킷)
        right_layout.addWidget(self.time_label)
        right_layout.addWidget(self.packet_label)

        # =========================================================
        # [4] Final Layout Construction
        # =========================================================
        layout.addWidget(left_container, 0, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title_container, 0, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(right_container, 0, 0, Qt.AlignmentFlag.AlignRight)

        # 1초마다 시간 업데이트 타이머
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    def update_time(self):
        """현재 UTC 시간을 업데이트"""
        now = datetime.datetime.utcnow().strftime("%H:%M:%S UTC")
        self.time_label.setText(now)

    def update_packet_count(self, count):
        """메인 윈도우에서 호출하여 패킷 수를 업데이트"""
        self.packet_label.setText(f"PACKETS: {count}")
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont

class EchoTerminal(QWidget):  # 메인 윈도우 연동을 위한 클래스명 유지
    def __init__(self):
        super().__init__()
        
        # 전체 레이아웃 설정 (여백 최소화)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        # 1. 상단 뷰 타이틀 안내 레이블 (Bold 적용)
        
        # 2. 메인 터미널 텍스트 에디터 생성
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)  # 로그 모니터이므로 수정 불가 고정
        
        # 가로 폭 부족 시 자동으로 다음 줄로 부드럽게 넘어가도록 래핑 설정
        self.terminal.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        
        # 순백색 배경(#ffffff), 진한 블랙(#111827) 기본 세팅 (전체 bold 스타일 제거)
        self.terminal.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        # 개발자 전용 고정폭 폰트(Consolas) 보통 두께로 지정
        font = QFont("Consolas", 11)
        self.terminal.setFont(font)
        
        layout.addWidget(self.terminal)

    def append_log(self, sender: str, text: str = None):
        """
        GCSBackend 시그널 포맷(sender, text)에 맞춘 로그 추가 메서드
        시간 부분만 <b> 태그를 적용해 굵게 출력합니다.
        """
        # main_window에서 단순 문자열 하나만 보냈을 때를 위한 예외 처리 가드
        if text is None:
            text = sender
            
        if not text:
            return
            
        # 1. 현재 시스템의 실시간 UTC 시간 추출 (HH:mm:ss)
        utc_now = QDateTime.currentDateTimeUtc().toString("HH:mm:ss")
        
        # 2. 시간은 <b> 태그로 감싸고 본문은 그대로 두어 두께를 이원화 (&nbsp;는 공백 확보용)
        formatted_log = f"<span style='color: #111827;'><b>[{utc_now}]--- </b>{text.strip()}</span>"
        
        # 3. HTML 형식으로 터미널에 로그 추가
        self.terminal.appendHtml(formatted_log)
        
        # 4. 새 로그가 들어오면 항상 최하단으로 자동 스크롤 고정
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_terminal(self):
        """터미널 화면 초기화 리셋 핸들러"""
        self.terminal.clear()
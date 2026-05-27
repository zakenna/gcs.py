from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont, QTextCursor

# 발신자별 색상 매핑
_SENDER_COLORS = {
    "CMD":       "#2563eb",  # 파랑  - 명령어
    "SIM":       "#c2410c",  # 주황  - 시뮬레이션
    "SYSTEM":    "#15803d",  # 초록  - 시스템
    "WARNING":   "#dc2626",  # 빨강  - 경고
    "FSW_DEBUG": "#6b7280",  # 회색  - FSW 디버그
    "FSW_TEXT":  "#374151",  # 진회색 - FSW 텍스트
}
_COLOR_DEFAULT = "#111827"
_MAX_LOG_LINES = 2000   # 최대 줄 수 (장시간 운용 메모리 누수 방지)


class EchoTerminal(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.terminal.setMaximumBlockCount(_MAX_LOG_LINES)  # 초과 시 오래된 줄 자동 제거
        self.terminal.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self.terminal.setFont(QFont("Consolas", 11))

        layout.addWidget(self.terminal)

    def append_log(self, sender: str, text: str = None):
        if text is None:
            text = sender
            sender = "SYSTEM"

        if not text:
            return

        utc_now = QDateTime.currentDateTimeUtc().toString("HH:mm:ss")
        color   = _SENDER_COLORS.get(sender, _COLOR_DEFAULT)

        # 발신자 태그를 색상으로 구분해서 어디서 온 로그인지 즉시 식별 가능
        html = (f"<span style='color:#6b7280;'><b>[{utc_now}]</b></span> "
                f"<span style='color:{color};'><b>[{sender}]</b></span> "
                f"<span style='color:{_COLOR_DEFAULT};'>{text.strip()}</span>")

        self.terminal.appendHtml(html)

        # 커서를 끝으로 이동 (scrollbar 직접 조작보다 안전)
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    def clear_terminal(self):
        self.terminal.clear()
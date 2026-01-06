# src/components/views/echo_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTextBrowser
from PyQt6.QtCore import Qt

class EchoTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; border: 1px solid #374151; border-radius: 6px; }
            QTextBrowser { background-color: #1e1e1e; color: #00ff00; font-family: 'Consolas'; border: none; font-size: 14px; padding: 10px; }
            QLabel { background-color: transparent; border: none; font-family: 'Segoe UI'; }
        """)

        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        lbl_title = QLabel("COMMAND ECHO TERMINAL")
        lbl_title.setStyleSheet("color: #d1d5db; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #374151; max-height: 1px;")

        self.terminal = QTextBrowser()
        
        layout.addLayout(header_layout)
        layout.addWidget(line)
        layout.addWidget(self.terminal)
        self.terminal.append("<div style='color: #6b7280;'>System Ready.</div>")

    def append_log(self, sender, text):
        html = f"""
        <div style='margin-bottom: 4px;'>
            <span style='color: #60a5fa; font-weight: bold;'>[{sender}]</span>
            <span style='color: #00ff00;'> {text}</span>
        </div>
        """
        self.terminal.append(html)
        # 스크롤 최하단으로 이동
        sb = self.terminal.verticalScrollBar()
        sb.setValue(sb.maximum())
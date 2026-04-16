from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class SectionWindow(QMainWindow):
    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.setWindowTitle(f"Gestión Hogar - {title}")
        self.resize(760, 480)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        message = QLabel(description)
        message.setWordWrap(True)

        layout.addWidget(header)
        layout.addWidget(message)
        layout.addStretch()
        self.setCentralWidget(central)

        self.setStyleSheet(
            """
            QMainWindow {
                background: #f6efe5;
            }
            QLabel {
                color: #223247;
            }
            """
        )

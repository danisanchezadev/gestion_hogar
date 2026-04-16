from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gestion_hogar.backend.service import FinanceService


class LoginWindow(QMainWindow):
    login_success = Signal(str)

    def __init__(self, service: FinanceService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("Acceso - Gestión Hogar")
        self.resize(420, 320)
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        title = QLabel("Gestión Hogar")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        subtitle = QLabel("Accede con tu usuario local para entrar en la aplicación.")
        subtitle.setWordWrap(True)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Usuario")
        self.username_input.setText("admin")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_button = QPushButton("Entrar")
        self.login_button.clicked.connect(self.attempt_login)

        hint = QLabel("Usuario inicial: admin | Contraseña inicial: admin")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.login_button)
        card_layout.addWidget(hint)

        layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        self.setCentralWidget(central)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #efe7da;
            }
            QFrame#loginCard {
                background: white;
                border: 1px solid #dfd2bf;
                border-radius: 24px;
            }
            QLabel {
                color: #233143;
            }
            QLineEdit {
                background: #fffdf8;
                color: #111111;
                border: 1px solid #d7cbb8;
                border-radius: 10px;
                padding: 10px;
            }
            QLineEdit::placeholder {
                color: #6b7280;
            }
            QPushButton {
                background: #1d4f91;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #163d71;
            }
            """
        )

    def attempt_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if self.service.authenticate_user(username, password):
            self.login_success.emit(username)
            self.close()
            return

        QMessageBox.warning(self, "Acceso denegado", "Usuario o contraseña incorrectos.")

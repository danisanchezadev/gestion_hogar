from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox

from gestion_hogar.backend.repository import SQLiteMovementRepository
from gestion_hogar.backend.service import FinanceService
from gestion_hogar.storage import DB_FILE, LEGACY_JSON_FILE
from gestion_hogar.ui.home_window import HomeWindow
from gestion_hogar.ui.login_window import LoginWindow


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    try:
        repository = SQLiteMovementRepository(DB_FILE)
        service = FinanceService(repository)
        service.bootstrap(LEGACY_JSON_FILE)
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Error de inicio",
            f"La aplicación no ha podido arrancar.\n\nDetalle: {exc}",
        )
        raise SystemExit(1)

    windows: list[HomeWindow] = []

    def open_main_window(username: str) -> None:
        window = HomeWindow(service, username)
        windows.append(window)
        window.show()

    login = LoginWindow(service)
    login.login_success.connect(open_main_window)
    login.show()
    app.exec()

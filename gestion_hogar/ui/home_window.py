from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gestion_hogar.backend.service import FinanceService
from gestion_hogar.ui.config_window import ConfigurationWindow
from gestion_hogar.ui.movements_window import MovementsWindow
from gestion_hogar.ui.section_window import SectionWindow


class NavigationCard(QFrame):
    def __init__(self, title: str, description: str, button_text: str, callback) -> None:
        super().__init__()
        self.setObjectName("navigationCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        description_label = QLabel(description)
        description_label.setWordWrap(True)

        action_button = QPushButton(button_text)
        action_button.clicked.connect(callback)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()
        layout.addWidget(action_button)


class HomeWindow(QMainWindow):
    def __init__(self, service: FinanceService, username: str) -> None:
        super().__init__()
        self.service = service
        self.username = username
        self.child_windows: list[QMainWindow] = []

        self.setWindowTitle("Gestión Hogar - Inicio")
        self.resize(1080, 680)
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(10)

        title = QLabel("Centro de control del hogar")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        subtitle = QLabel(
            f"Sesión iniciada como {self.username}. Desde aquí puedes entrar a cada parte de la aplicación."
        )
        subtitle.setWordWrap(True)

        summary = self.service.get_summary()
        balance_label = QLabel(
            f"Ingresos acumulados: {summary.ingresos:.2f} EUR   |   "
            f"Gastos acumulados: {summary.gastos:.2f} EUR   |   "
            f"Inversiones acumuladas: {summary.inversiones:.2f} EUR   |   "
            f"Balance: {summary.balance:.2f} EUR"
        )
        balance_label.setObjectName("heroSummary")
        balance_label.setWordWrap(True)

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addWidget(balance_label)

        cards = QWidget()
        cards_layout = QGridLayout(cards)
        cards_layout.setSpacing(16)

        cards_layout.addWidget(
            NavigationCard(
                "Configuración de categorías",
                "Gestiona categorías personalizadas de ingresos, gastos e inversiones para clasificar mejor tus movimientos.",
                "Abrir configuración",
                self.open_configuration,
            ),
            0,
            0,
        )
        cards_layout.addWidget(
            NavigationCard(
                "Vista del mes",
                "Consulta el estado mensual del hogar y prepara el seguimiento del objetivo 50/30/10/10.",
                "Abrir vista del mes",
                self.open_month_view,
            ),
            0,
            1,
        )
        cards_layout.addWidget(
            NavigationCard(
                "Agregar movimiento",
                "Accede al módulo para registrar nuevos ingresos, gastos e inversiones del hogar.",
                "Abrir agregar movimiento",
                self.open_movements,
            ),
            1,
            0,
        )
        cards_layout.addWidget(
            NavigationCard(
                "Evolución mensual",
                "Reserva este espacio para los gráficos de barras y la comparativa histórica entre meses.",
                "Abrir evolución",
                self.open_evolution,
            ),
            1,
            1,
        )

        layout.addWidget(hero)
        layout.addWidget(cards)
        self.setCentralWidget(central)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f3ecdf;
            }
            QFrame#heroPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #133c73, stop:1 #2f6cb3);
                border-radius: 28px;
            }
            QFrame#heroPanel QLabel {
                color: white;
            }
            QLabel#heroSummary {
                background: rgba(255, 255, 255, 0.14);
                border-radius: 14px;
                padding: 12px;
            }
            QFrame#navigationCard {
                background: white;
                border: 1px solid #e0d3c0;
                border-radius: 22px;
            }
            QLabel {
                color: #213245;
            }
            QPushButton {
                background: #184f96;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #123e75;
            }
            """
        )

    def _show_child(self, window: QMainWindow) -> None:
        self.child_windows.append(window)
        window.show()

    def open_configuration(self) -> None:
        window = ConfigurationWindow(self.service)
        window.category_changed.connect(self._refresh_open_movement_windows)
        self._show_child(window)

    def open_month_view(self) -> None:
        try:
            import importlib
            import gestion_hogar.ui.month_view_window as month_view_window

            importlib.reload(month_view_window)

            self._show_child(month_view_window.MonthViewWindow(self.service))
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error al abrir Vista del mes",
                f"No se ha podido abrir la ventana.\n\nDetalle: {exc}",
            )

    def open_movements(self) -> None:
        self._show_child(MovementsWindow(self.service, self.username))

    def open_evolution(self) -> None:
        self._show_child(
            SectionWindow(
                "Evolución mensual",
                "Aquí montaremos los gráficos de barras para comparar ingresos y gastos por meses.",
            )
        )

    def _refresh_open_movement_windows(self) -> None:
        for window in self.child_windows:
            if isinstance(window, MovementsWindow):
                window.reload_categories()

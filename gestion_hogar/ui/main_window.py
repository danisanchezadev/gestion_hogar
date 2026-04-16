from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gestion_hogar.models import (
    CATEGORY_TYPES,
    MOVEMENT_TYPES,
    NATURE_LABELS,
    TYPE_LABELS,
    Transaction,
)
from gestion_hogar.backend.service import FinanceService


def money(value: float) -> str:
    return f"{value:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")


class SummaryCard(QFrame):
    def __init__(self, title: str, color: str) -> None:
        super().__init__()
        self.setObjectName("summaryCard")
        self.setStyleSheet(
            f"""
            QFrame#summaryCard {{
                background-color: {color};
                border-radius: 18px;
                padding: 12px;
            }}
            QLabel {{
                color: white;
            }}
            """
        )

        layout = QVBoxLayout(self)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 13px;")
        self.value_label = QLabel("0,00 EUR")
        self.value_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addStretch()

    def set_value(self, value: float) -> None:
        self.value_label.setText(money(value))


class MovementsWindow(QMainWindow):
    def __init__(self, service: FinanceService, username: str) -> None:
        super().__init__()
        self.service = service
        self.username = username
        self.tables: dict[str, QTableWidget] = {}

        self.setWindowTitle("Gestión Hogar - Agregar movimiento")
        self.resize(1180, 720)
        self._build_ui()
        self._apply_styles()
        self.refresh_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        root.addWidget(self._build_form_panel(), 1)
        root.addWidget(self._build_dashboard_panel(), 2)
        self.setCentralWidget(central)

    def _build_form_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("sidePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        title = QLabel("Agregar movimiento")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setObjectName("sectionTitle")
        subtitle = QLabel(f"Sesión iniciada como {self.username}. Registra ingresos, gastos e inversiones del hogar.")
        subtitle.setWordWrap(True)

        form_box = QGroupBox("Datos")
        form_layout = QFormLayout(form_box)

        self.type_combo = QComboBox()
        for movement_type in MOVEMENT_TYPES:
            self.type_combo.addItem(TYPE_LABELS[movement_type], movement_type)
        self.type_combo.currentIndexChanged.connect(self._update_subcategories)

        self.category_combo = QComboBox()
        for category in CATEGORY_TYPES:
            self.category_combo.addItem(NATURE_LABELS[category], category)
        self.category_combo.currentIndexChanged.connect(self._update_subcategories)

        self.subcategory_combo = QComboBox()
        self.subcategory_combo.setEditable(True)
        self._update_subcategories()

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(1_000_000)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix("EUR ")
        self.amount_input.setMinimum(0.01)
        self.amount_input.setValue(50.0)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())

        form_layout.addRow("Tipo", self.type_combo)
        form_layout.addRow("Categoría", self.category_combo)
        form_layout.addRow("Subcategoría", self.subcategory_combo)
        form_layout.addRow("Importe", self.amount_input)
        form_layout.addRow("Fecha", self.date_input)

        self.add_button = QPushButton("Guardar movimiento")
        self.add_button.clicked.connect(self.add_transaction)

        info_box = QGroupBox("Base de datos local")
        info_layout = QVBoxLayout(info_box)
        data_path = Path(self.service.repository.db_path)
        info_layout.addWidget(QLabel("Los datos se guardan solo en este equipo, en una base SQLite local."))
        info_layout.addWidget(QLabel(str(data_path)))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(form_box)
        layout.addWidget(self.add_button)
        layout.addWidget(info_box)
        layout.addStretch()
        return panel

    def _build_dashboard_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(18)

        header = QLabel("Panel financiero del hogar")
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.setObjectName("sectionTitle")
        desc = QLabel("Resumen rápido de ingresos, gastos, inversiones y balance disponible.")
        desc.setStyleSheet("color: #5f6b7a;")

        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(12)

        self.summary_cards = {
            "income": SummaryCard("Ingresos", "#177245"),
            "expense": SummaryCard("Gastos", "#b42318"),
            "investment": SummaryCard("Inversiones", "#175cd3"),
            "balance": SummaryCard("Balance", "#7a2e98"),
        }

        cards_layout.addWidget(self.summary_cards["income"], 0, 0)
        cards_layout.addWidget(self.summary_cards["expense"], 0, 1)
        cards_layout.addWidget(self.summary_cards["investment"], 1, 0)
        cards_layout.addWidget(self.summary_cards["balance"], 1, 1)

        self.insight_label = QLabel()
        self.insight_label.setWordWrap(True)
        self.insight_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.tabs = QTabWidget()
        for movement_type in MOVEMENT_TYPES:
            table = QTableWidget(0, 4)
            table.setHorizontalHeaderLabels(["Fecha", "Categoría", "Subcategoría", "Importe"])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.tables[movement_type] = table
            self.tabs.addTab(table, TYPE_LABELS[movement_type] + "s")

        layout.addWidget(header)
        layout.addWidget(desc)
        layout.addWidget(cards_widget)
        layout.addWidget(self.insight_label)
        layout.addWidget(self.tabs)
        return panel

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5eee4;
            }
            QFrame#sidePanel {
                background: white;
                border: 1px solid #e4d7c5;
                border-radius: 24px;
            }
            QLabel {
                color: #213245;
                font-size: 15px;
            }
            QLabel#sectionTitle {
                color: #111111;
                font-size: 18px;
                font-weight: 700;
            }
            QGroupBox {
                font-weight: 600;
                border: 1px solid #e4d7c5;
                border-radius: 16px;
                margin-top: 12px;
                padding: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #213245;
            }
            QComboBox, QDateEdit, QDoubleSpinBox, QTableWidget, QTabWidget::pane {
                background: white;
                color: #111111;
                border: 1px solid #d7cbb8;
                border-radius: 10px;
                padding: 8px;
                font-size: 15px;
            }
            QComboBox, QDateEdit, QDoubleSpinBox {
                min-height: 22px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #fbf7f0);
            }
            QComboBox:hover, QDateEdit:hover, QDoubleSpinBox:hover {
                border: 1px solid #c6b49a;
            }
            QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus {
                border: 1px solid #1d4f91;
            }
            QComboBox::drop-down, QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #d7cbb8;
                background: #f7f1e7;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QComboBox::down-arrow, QDateEdit::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/arrowdown-16.png);
                width: 14px;
                height: 14px;
            }
            QComboBox QAbstractItemView {
                color: #111111;
                background: white;
                font-size: 15px;
                border: 1px solid #d7cbb8;
                selection-background-color: #e9f0fb;
                selection-color: #111111;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f6efe3, stop:1 #efe2cc);
                color: #213245;
                border: none;
                border-bottom: 1px solid #dfcfb8;
                padding: 12px 8px;
                font-size: 15px;
                font-weight: 600;
                text-align: center;
            }
            QTableWidget {
                gridline-color: #eadfce;
                selection-background-color: #dfeafb;
                selection-color: #111111;
            }
            QPushButton {
                background: #1d4f91;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                font-weight: 700;
                font-size: 15px;
            }
            QPushButton:hover {
                background: #163d71;
            }
            QTabBar::tab {
                background: #efe2cc;
                color: #213245;
                padding: 10px 16px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #111111;
            }
            QTableCornerButton::section {
                background: #f7f1e7;
                border: none;
                border-bottom: 1px solid #e4d7c5;
            }
            """
        )

    def _update_subcategories(self) -> None:
        movement_type = self.type_combo.currentData() if hasattr(self, "type_combo") else MOVEMENT_TYPES[0]
        subtype = self.category_combo.currentData() if hasattr(self, "category_combo") else CATEGORY_TYPES[0]
        current_text = self.subcategory_combo.currentText() if hasattr(self, "subcategory_combo") else ""
        available = [
            item.nombre
            for item in self.service.list_custom_categories(active_only=True)
            if item.tipo_movimiento == movement_type and item.naturaleza == subtype
        ]

        self.subcategory_combo.clear()
        self.subcategory_combo.addItems(available)
        if current_text:
            self.subcategory_combo.setEditText(current_text)

    def reload_categories(self) -> None:
        self._update_subcategories()

    def add_transaction(self) -> None:
        subcategory = self.subcategory_combo.currentText().strip()
        if not subcategory:
            QMessageBox.warning(self, "Subcategoría vacía", "Introduce una subcategoría para el movimiento.")
            return

        transaction = Transaction(
            cantidad=self.amount_input.value(),
            tipo=self.type_combo.currentData(),
            categoria=self.category_combo.currentData(),
            subcategoria=subcategory,
            fecha=self.date_input.date().toString("yyyy-MM-dd"),
            id=None,
        )
        self.service.create_movement(
            cantidad=transaction.cantidad,
            tipo=transaction.tipo,
            categoria=transaction.categoria,
            subcategoria=transaction.subcategoria,
            fecha=transaction.fecha,
        )
        self.subcategory_combo.setEditText("")
        self.amount_input.setValue(50.0)
        self.refresh_ui()
        QMessageBox.information(self, "Movimiento guardado", "El movimiento se ha guardado correctamente.")

    def refresh_ui(self) -> None:
        summary = self.service.get_summary()
        self.summary_cards["income"].set_value(summary.ingresos)
        self.summary_cards["expense"].set_value(summary.gastos)
        self.summary_cards["investment"].set_value(summary.inversiones)
        self.summary_cards["balance"].set_value(summary.balance)

        balance = summary.balance
        color = QColor("#177245" if balance >= 0 else "#b42318").name()
        self.insight_label.setStyleSheet(
            f"background: white; border-radius: 16px; padding: 14px; border: 1px solid #e7dccd; color: {color};"
        )
        self.insight_label.setText(
            "Balance disponible actual: "
            f"{money(balance)}\n"
            f"Ingreso medio registrado: {money(self.service.get_average('ingreso'))} | "
            f"Gasto medio registrado: {money(self.service.get_average('gasto'))} | "
            f"Inversión media registrada: {money(self.service.get_average('inversion'))}"
        )

        movements = self.service.list_movements()
        for movement_type, table in self.tables.items():
            items = [item for item in movements if item.tipo == movement_type]
            table.setRowCount(len(items))
            for row, item in enumerate(items):
                table.setItem(row, 0, QTableWidgetItem(item.fecha))
                table.setItem(row, 1, QTableWidgetItem(item.categoria.capitalize()))
                table.setItem(row, 2, QTableWidgetItem(item.subcategoria))
                amount_cell = QTableWidgetItem(money(item.cantidad))
                amount_cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, 3, amount_cell)
            table.resizeColumnsToContents()


def run(service: FinanceService, username: str) -> MovementsWindow:
    app = QApplication.instance() or QApplication([])
    window = MovementsWindow(service, username)
    window.show()
    if QApplication.instance() is app:
        app.exec()
    return window


MainWindow = MovementsWindow

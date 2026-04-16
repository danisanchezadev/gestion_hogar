from __future__ import annotations

from collections import defaultdict

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalBarSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from gestion_hogar.backend.entities import CATEGORY_TYPES, Movement
from gestion_hogar.backend.service import FinanceService


SUBTYPE_LABELS = {
    "fijo": "Fijo",
    "variable": "Variable",
    "inesperado": "Inesperado",
}

SUBTYPE_COLORS = {
    "fijo": "#efb7ae",
    "variable": "#f4d38d",
    "inesperado": "#d88b8b",
}


def money(value: float) -> str:
    return f"{value:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")


class MonthViewWindow(QMainWindow):
    def __init__(self, service: FinanceService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("Gestión Hogar - Vista del mes")
        self.resize(1240, 820)
        self._build_ui()
        self._apply_styles()
        self.refresh_view()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(22, 22, 22, 22)
        header_layout.setSpacing(12)

        title = QLabel("Vista del mes")
        title.setObjectName("sectionTitle")
        subtitle = QLabel(
            "Resumen visual del mes con distribución de ingresos, gastos e inversiones."
        )
        subtitle.setWordWrap(True)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        month_label = QLabel("Mes a consultar")
        self.month_input = QDateEdit()
        self.month_input.setCalendarPopup(True)
        self.month_input.setDisplayFormat("MMMM yyyy")
        self.month_input.setDate(QDate.currentDate())
        self.month_input.dateChanged.connect(self.refresh_view)
        controls.addWidget(month_label)
        controls.addWidget(self.month_input)
        controls.addStretch()

        self.month_totals_label = QLabel()
        self.month_totals_label.setObjectName("summaryText")
        self.month_totals_label.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addLayout(controls)
        header_layout.addWidget(self.month_totals_label)

        charts_grid = QGridLayout()
        charts_grid.setSpacing(16)

        self.month_overview_chart, self.month_overview_chart_view = self._create_chart_container(
            "Gastos respecto del 100% ingresado"
        )
        self.income_chart, self.income_chart_view = self._create_chart_container(
            "Distribución de ingresos"
        )
        self.expense_chart, self.expense_chart_view = self._create_chart_container(
            "Gastos por subcategoría"
        )
        self.investment_chart, self.investment_chart_view = self._create_chart_container(
            "Inversiones por subcategoría"
        )

        charts_grid.addWidget(self.month_overview_chart, 0, 0)
        charts_grid.addWidget(self.income_chart, 0, 1)
        charts_grid.addWidget(self.expense_chart, 1, 0)
        charts_grid.addWidget(self.investment_chart, 1, 1)

        root.addWidget(header_card)
        root.addLayout(charts_grid, 1)
        self.setCentralWidget(central)

    def _create_chart_container(self, title: str) -> tuple[QFrame, QChartView]:
        frame = QFrame()
        frame.setObjectName("chartCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        label = QLabel(title)
        label.setObjectName("cardTitle")
        chart_view = QChartView()
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(280)

        layout.addWidget(label)
        layout.addWidget(chart_view, 1)
        return frame, chart_view

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5eee4;
            }
            QFrame#headerCard, QFrame#chartCard {
                background: white;
                border: 1px solid #e4d7c5;
                border-radius: 18px;
            }
            QLabel {
                color: #213245;
                font-size: 15px;
            }
            QLabel#sectionTitle {
                color: #111111;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#cardTitle {
                color: #111111;
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#summaryText {
                color: #4e5d6f;
                font-size: 14px;
            }
            QDateEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #fbf7f0);
                color: #111111;
                border: 1px solid #d7cbb8;
                border-radius: 10px;
                padding: 8px;
                font-size: 15px;
                min-height: 22px;
            }
            QDateEdit:hover {
                border: 1px solid #c6b49a;
            }
            QDateEdit:focus {
                border: 1px solid #1d4f91;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #d7cbb8;
                background: #f7f1e7;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QDateEdit::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/arrowdown-16.png);
                width: 14px;
                height: 14px;
            }
            QChartView {
                border: none;
                background: transparent;
            }
            """
        )

    def refresh_view(self) -> None:
        month_date = self.month_input.date()
        month_key = month_date.toString("yyyy-MM")
        month_movements = [
            movement
            for movement in self.service.list_movements()
            if movement.fecha.startswith(month_key)
        ]

        income_total = sum(item.cantidad for item in month_movements if item.tipo == "ingreso")
        expense_total = sum(item.cantidad for item in month_movements if item.tipo == "gasto")
        investment_total = sum(item.cantidad for item in month_movements if item.tipo == "inversion")

        self.month_totals_label.setText(
            f"Ingresos: {money(income_total)}   |   "
            f"Gastos: {money(expense_total)}   |   "
            f"Inversiones: {money(investment_total)}"
        )

        self.month_overview_chart_view.setChart(
            self._build_month_overview_chart(month_movements, income_total)
        )
        self.income_chart_view.setChart(
            self._build_subtype_pie_chart(month_movements, "ingreso", "Ingresos del mes")
        )
        self.expense_chart_view.setChart(
            self._build_subcategory_bar_chart(month_movements, "gasto", "Gastos por subcategoría")
        )
        self.investment_chart_view.setChart(
            self._build_subcategory_bar_chart(
                month_movements, "inversion", "Inversiones por subcategoría"
            )
        )

    def _build_month_overview_chart(self, movements: list[Movement], income_total: float) -> QChart:
        by_subtype = {
            subtype: sum(
                item.cantidad
                for item in movements
                if item.tipo == "gasto" and item.categoria == subtype
            )
            for subtype in CATEGORY_TYPES
        }

        series = QPieSeries()
        for subtype in CATEGORY_TYPES:
            amount = by_subtype[subtype]
            if amount <= 0:
                continue
            slice_ = series.append(f"Gasto {SUBTYPE_LABELS[subtype]}", amount)
            slice_.setBrush(QBrush(QColor(SUBTYPE_COLORS[subtype])))
            slice_.setLabelVisible(True)

        spent = sum(by_subtype.values())
        remaining = max(0.0, income_total - spent)
        exceeded = max(0.0, spent - income_total)
        if remaining > 0:
            slice_ = series.append("Disponible", remaining)
            slice_.setBrush(QBrush(QColor("#8cc9a5")))
            slice_.setLabelVisible(True)
        if exceeded > 0:
            slice_ = series.append("Exceso de gasto", exceeded)
            slice_.setBrush(QBrush(QColor("#8d2f2f")))
            slice_.setLabelVisible(True)

        chart = QChart()
        chart.setTitle("Gastos frente al ingreso del mes")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        if series.count() == 0:
            chart.setTitle("Gastos frente al ingreso del mes - sin datos")
            return chart
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        return chart

    def _build_subtype_pie_chart(
        self,
        movements: list[Movement],
        movement_type: str,
        title: str,
    ) -> QChart:
        series = QPieSeries()
        for subtype in CATEGORY_TYPES:
            amount = sum(
                item.cantidad
                for item in movements
                if item.tipo == movement_type and item.categoria == subtype
            )
            if amount <= 0:
                continue
            slice_ = series.append(SUBTYPE_LABELS[subtype], amount)
            slice_.setBrush(QBrush(QColor(SUBTYPE_COLORS[subtype])))
            slice_.setLabelVisible(True)

        chart = QChart()
        chart.setTitle(title if series.count() else f"{title} - sin datos")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        if series.count():
            chart.addSeries(series)
            chart.legend().setVisible(True)
            chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        return chart

    def _build_subcategory_bar_chart(
        self,
        movements: list[Movement],
        movement_type: str,
        title: str,
    ) -> QChart:
        by_subcategory: dict[str, float] = defaultdict(float)
        for item in movements:
            if item.tipo == movement_type:
                by_subcategory[item.subcategoria] += item.cantidad

        chart = QChart()
        chart.setTitle(title if by_subcategory else f"{title} - sin datos")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        if not by_subcategory:
            return chart

        sorted_items = sorted(by_subcategory.items(), key=lambda pair: pair[1], reverse=True)
        categories = [name for name, _ in sorted_items]
        values = [value for _, value in sorted_items]

        bar_set = QBarSet("Importe")
        bar_set.append(values)
        if movement_type == "gasto":
            bar_set.setColor("#d88b8b")
        elif movement_type == "inversion":
            bar_set.setColor("#7fa8e8")
        else:
            bar_set.setColor("#8cc9a5")

        series = QHorizontalBarSeries()
        series.append(bar_set)
        chart.addSeries(series)

        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        axis_x = QValueAxis()
        axis_x.setLabelFormat("%.0f")
        axis_x.setTitleText("EUR")
        axis_x.setRange(0, max(values) * 1.15 if values else 1)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        chart.legend().setVisible(False)
        return chart

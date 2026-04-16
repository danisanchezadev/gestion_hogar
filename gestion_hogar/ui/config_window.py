from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from gestion_hogar.backend.entities import CustomCategory
from gestion_hogar.backend.service import FinanceService
from gestion_hogar.models import (
    CATEGORY_TYPES,
    ESSENTIAL_LABELS,
    FREQUENCY_LABELS,
    FREQUENCY_TYPES,
    MOVEMENT_TYPES,
    NATURE_LABELS,
    STATUS_LABELS,
    TYPE_LABELS,
)


def _category_tooltip(category: CustomCategory) -> str:
    return (
        f"Descripción: {category.descripcion or 'Sin descripción'}\n"
        f"Grupo: {category.grupo or 'Sin grupo'}\n"
        f"Frecuencia: {FREQUENCY_LABELS.get(category.frecuencia, 'Sin definir')}\n"
        f"Estado: {STATUS_LABELS[category.activa]}"
    )


class CategoryEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        title: str,
        category: CustomCategory | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(700, 620)
        self._build_ui()
        self._apply_styles()
        if category is not None:
            self.load_category(category)
        self._sync_accept_button()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(self.windowTitle())
        title.setObjectName("dialogTitle")
        subtitle = QLabel(
            "Revisa bien el nombre, la naturaleza y el grupo para mantener una clasificación clara y útil."
        )
        subtitle.setWordWrap(True)

        identity_box = QGroupBox("Datos principales")
        identity_layout = QFormLayout(identity_box)
        identity_layout.setVerticalSpacing(14)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ejemplo: Combustible")
        self.name_input.textChanged.connect(self._sync_accept_button)

        self.type_combo = QComboBox()
        for movement_type in MOVEMENT_TYPES:
            self.type_combo.addItem(TYPE_LABELS[movement_type], movement_type)

        self.nature_combo = QComboBox()
        for nature in CATEGORY_TYPES:
            self.nature_combo.addItem(NATURE_LABELS[nature], nature)

        identity_layout.addRow("Nombre", self.name_input)
        identity_layout.addRow("Tipo", self.type_combo)
        identity_layout.addRow("Naturaleza", self.nature_combo)

        context_box = QGroupBox("Contexto y clasificación")
        context_layout = QFormLayout(context_box)
        context_layout.setVerticalSpacing(14)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Descripción breve opcional")
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("Ejemplo: Transporte, Vivienda, Alimentación")

        context_layout.addRow("Descripción", self.description_input)
        context_layout.addRow("Grupo", self.group_input)

        analysis_box = QGroupBox("Planificación y estado")
        analysis_layout = QFormLayout(analysis_box)
        analysis_layout.setVerticalSpacing(14)

        self.essential_combo = QComboBox()
        self.essential_combo.addItem("Sí", True)
        self.essential_combo.addItem("No", False)
        self.essential_combo.setCurrentIndex(1)

        self.frequency_combo = QComboBox()
        self.frequency_combo.addItem("Sin definir", "")
        for frequency in FREQUENCY_TYPES:
            self.frequency_combo.addItem(FREQUENCY_LABELS[frequency], frequency)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Activa", True)
        self.status_combo.addItem("Archivada", False)

        analysis_layout.addRow("Esencial", self.essential_combo)
        analysis_layout.addRow("Frecuencia", self.frequency_combo)
        analysis_layout.addRow("Estado", self.status_combo)

        self.validation_label = QLabel("El nombre es obligatorio.")
        self.validation_label.setObjectName("validationLabel")

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)

        self.accept_button = QPushButton("Guardar")
        self.accept_button.clicked.connect(self.accept)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.accept_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(identity_box)
        layout.addWidget(context_box)
        layout.addWidget(analysis_box)
        layout.addWidget(self.validation_label)
        layout.addStretch()
        layout.addLayout(buttons)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog { background: #f5eee4; }
            QLabel { color: #213245; font-size: 15px; }
            QLabel#dialogTitle { color: #111111; font-size: 22px; font-weight: 700; }
            QLabel#validationLabel { color: #b42318; font-size: 14px; font-weight: 600; }
            QGroupBox {
                border: 1px solid #e4d7c5; border-radius: 16px; padding: 16px 14px 14px 14px;
                background: white; font-size: 15px; font-weight: 700; color: #213245;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
            QLineEdit, QComboBox {
                background: white; color: #111111; border: 1px solid #d7cbb8;
                border-radius: 10px; padding: 10px 14px; font-size: 15px; min-height: 22px;
            }
            QComboBox {
                padding-right: 40px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #fbf7f0);
            }
            QComboBox:hover, QLineEdit:hover { border: 1px solid #c6b49a; }
            QComboBox:focus, QLineEdit:focus { border: 1px solid #1d4f91; }
            QComboBox::drop-down {
                subcontrol-origin: padding; subcontrol-position: top right; width: 30px;
                border-left: 1px solid #d7cbb8; background: #f7f1e7;
                border-top-right-radius: 10px; border-bottom-right-radius: 10px;
            }
            QComboBox::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/arrowdown-16.png);
                width: 14px; height: 14px;
            }
            QComboBox QAbstractItemView {
                color: #111111; background: white; font-size: 15px; border: 1px solid #d7cbb8;
                selection-background-color: #e9f0fb; selection-color: #111111;
            }
            QPushButton {
                background: #1d4f91; color: white; border: none; border-radius: 12px;
                padding: 12px 16px; font-weight: 700; font-size: 15px; min-width: 140px;
            }
            QPushButton:hover { background: #163d71; }
            QPushButton:disabled { background: #9fb4d2; color: #eff4fb; }
            QPushButton#secondaryButton { background: #efe2cc; color: #213245; }
            QPushButton#secondaryButton:hover { background: #e7d8c1; }
            """
        )

    def _sync_accept_button(self) -> None:
        has_name = bool(self.name_input.text().strip())
        self.accept_button.setEnabled(has_name)
        self.validation_label.setVisible(not has_name)

    def load_category(self, category: CustomCategory) -> None:
        self.name_input.setText(category.nombre)
        self.description_input.setText(category.descripcion)
        self.group_input.setText(category.grupo)
        self.type_combo.setCurrentIndex(self.type_combo.findData(category.tipo_movimiento))
        self.nature_combo.setCurrentIndex(self.nature_combo.findData(category.naturaleza))
        self.essential_combo.setCurrentIndex(self.essential_combo.findData(category.esencial))
        self.frequency_combo.setCurrentIndex(self.frequency_combo.findData(category.frecuencia))
        self.status_combo.setCurrentIndex(self.status_combo.findData(category.activa))

    def payload(self) -> dict[str, object]:
        return {
            "nombre": self.name_input.text(),
            "descripcion": self.description_input.text(),
            "tipo_movimiento": self.type_combo.currentData(),
            "naturaleza": self.nature_combo.currentData(),
            "grupo": self.group_input.text(),
            "esencial": bool(self.essential_combo.currentData()),
            "frecuencia": self.frequency_combo.currentData(),
            "activa": bool(self.status_combo.currentData()),
        }


class ConfigurationWindow(QMainWindow):
    category_changed = Signal()

    TYPE_ROW_COLORS = {
        "gasto": "#fdf0ee",
        "ingreso": "#eef8f1",
        "inversion": "#eef4fd",
    }

    def __init__(self, service: FinanceService) -> None:
        super().__init__()
        self.service = service
        self._all_categories: list[CustomCategory] = []
        self._displayed_categories: list[CustomCategory] = []
        self._sort_column = 1
        self._sort_descending = False

        self.setWindowTitle("Gestión Hogar - Configuración de categorías")
        self.resize(1280, 880)
        self.setMinimumSize(1140, 780)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        self._build_ui()
        self._apply_styles()
        self.refresh_categories()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        title = QLabel("Configuración de categorías")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        subtitle = QLabel(
            "Consulta, filtra y gestiona tus categorías. El alta y la edición se hacen en una ventana limpia aparte."
        )
        subtitle.setWordWrap(True)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.new_button = QPushButton("Nueva categoría")
        self.new_button.clicked.connect(self.open_new_category_dialog)
        self.new_button.setToolTip("Abre el diálogo para crear una nueva categoría.")

        self.edit_button = QPushButton("Editar categoría marcada")
        self.edit_button.clicked.connect(self.open_edit_category_dialog)
        self.edit_button.setToolTip("Edita la fila marcada de la tabla.")

        self.archive_button = QPushButton("Archivar o activar marcadas")
        self.archive_button.clicked.connect(self.toggle_checked_category_status)
        self.archive_button.setToolTip("Cambia el estado de las categorías marcadas con checkbox.")

        self.delete_button = QPushButton("Eliminar categorías marcadas")
        self.delete_button.clicked.connect(self.delete_checked_categories)
        self.delete_button.setToolTip("Elimina o archiva inteligentemente las categorías marcadas.")

        top_bar.addWidget(self.new_button)
        top_bar.addWidget(self.edit_button)
        top_bar.addWidget(self.archive_button)
        top_bar.addWidget(self.delete_button)

        body = QGridLayout()
        body.setHorizontalSpacing(18)
        body.setVerticalSpacing(18)
        body.addWidget(self._build_filters_box(), 0, 0)
        body.addWidget(self._build_summary_box(), 1, 0)
        body.addWidget(self._build_table_box(), 0, 1, 2, 1)
        body.setColumnStretch(0, 4)
        body.setColumnStretch(1, 10)
        body.setRowStretch(1, 1)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addLayout(top_bar)
        root.addLayout(body, 1)
        self.setCentralWidget(central)

    def _build_filters_box(self) -> QGroupBox:
        box = QGroupBox()
        layout = QGridLayout(box)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        title = QLabel("Filtros y búsqueda")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Buscar por nombre, descripción o grupo")
        self.filter_input.textChanged.connect(self.apply_category_filters)

        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("Todos", "")
        for movement_type in MOVEMENT_TYPES:
            self.filter_type_combo.addItem(TYPE_LABELS[movement_type], movement_type)
        self.filter_type_combo.currentIndexChanged.connect(self.apply_category_filters)

        self.filter_nature_combo = QComboBox()
        self.filter_nature_combo.addItem("Todas", "")
        for nature in CATEGORY_TYPES:
            self.filter_nature_combo.addItem(NATURE_LABELS[nature], nature)
        self.filter_nature_combo.currentIndexChanged.connect(self.apply_category_filters)

        self.filter_group_combo = QComboBox()
        self.filter_group_combo.addItem("Todos", "")
        self.filter_group_combo.currentIndexChanged.connect(self.apply_category_filters)

        self.filter_essential_combo = QComboBox()
        self.filter_essential_combo.addItem("Todos", "all")
        self.filter_essential_combo.addItem("Esenciales", "yes")
        self.filter_essential_combo.addItem("No esenciales", "no")
        self.filter_essential_combo.currentIndexChanged.connect(self.apply_category_filters)

        self.filter_status_combo = QComboBox()
        self.filter_status_combo.addItem("Todas", "all")
        self.filter_status_combo.addItem("Activas", "active")
        self.filter_status_combo.addItem("Archivadas", "archived")
        self.filter_status_combo.currentIndexChanged.connect(self.apply_category_filters)

        self.filter_frequency_combo = QComboBox()
        self.filter_frequency_combo.addItem("Todas", "all")
        self.filter_frequency_combo.addItem("Sin definir", "__none__")
        for frequency in FREQUENCY_TYPES:
            self.filter_frequency_combo.addItem(FREQUENCY_LABELS[frequency], frequency)
        self.filter_frequency_combo.currentIndexChanged.connect(self.apply_category_filters)

        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(QLabel("Buscar"), 1, 0)
        layout.addWidget(self.filter_input, 1, 1, 1, 3)
        layout.addWidget(QLabel("Tipo"), 2, 0)
        layout.addWidget(self.filter_type_combo, 2, 1)
        layout.addWidget(QLabel("Naturaleza"), 2, 2)
        layout.addWidget(self.filter_nature_combo, 2, 3)
        layout.addWidget(QLabel("Grupo"), 3, 0)
        layout.addWidget(self.filter_group_combo, 3, 1)
        layout.addWidget(QLabel("Esencial"), 3, 2)
        layout.addWidget(self.filter_essential_combo, 3, 3)
        layout.addWidget(QLabel("Estado"), 4, 0)
        layout.addWidget(self.filter_status_combo, 4, 1)
        layout.addWidget(QLabel("Frecuencia"), 4, 2)
        layout.addWidget(self.filter_frequency_combo, 4, 3)
        return box

    def _build_summary_box(self) -> QGroupBox:
        box = QGroupBox()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Resumen global de categorías")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.visible_label = QLabel()
        self.total_label = QLabel()
        self.state_label = QLabel()
        self.type_label = QLabel()
        self.nature_label = QLabel()
        self.essential_label = QLabel()

        detail_title = QLabel("Detalle de la categoría seleccionada")
        detail_title.setObjectName("sectionTitle")
        detail_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.selected_name_label = QLabel("Ninguna categoría seleccionada.")
        self.selected_description_label = QLabel("Descripción: selecciona una fila para ver más detalle.")
        self.selected_description_label.setWordWrap(True)
        self.selected_meta_label = QLabel("")
        self.selected_meta_label.setWordWrap(True)

        self.checked_count_label = QLabel()
        self.checked_count_label.setObjectName("summaryCounter")

        content_widget = QWidget()
        content_widget.setObjectName("summaryContent")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        content_layout.addWidget(self.visible_label)
        content_layout.addWidget(self.total_label)
        content_layout.addWidget(self.state_label)
        content_layout.addWidget(self.type_label)
        content_layout.addWidget(self.nature_label)
        content_layout.addWidget(self.essential_label)
        content_layout.addSpacing(6)
        content_layout.addWidget(detail_title)
        content_layout.addWidget(self.selected_name_label)
        content_layout.addWidget(self.selected_description_label)
        content_layout.addWidget(self.selected_meta_label)
        content_layout.addStretch()
        content_layout.addWidget(self.checked_count_label)

        scroll = QScrollArea()
        scroll.setObjectName("summaryScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content_widget)

        layout.addWidget(title)
        layout.addWidget(scroll)
        return box

    def _build_table_box(self) -> QGroupBox:
        box = QGroupBox()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Tabla de categorías")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addStretch()
        title_row.addWidget(title)
        title_row.addStretch()

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["", "Nombre", "Tipo", "Naturaleza", "Grupo", "Esencial", "Frecuencia", "Estado"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        self.table.setWordWrap(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self.open_edit_category_dialog())

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumSectionSize(84)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.sectionClicked.connect(self._handle_header_sort)
        header.sectionResized.connect(lambda *_args: self._position_header_checkbox())
        header.geometriesChanged.connect(self._position_header_checkbox)

        self.toggle_all_checkbox = QCheckBox(header.viewport())
        self.toggle_all_checkbox.setObjectName("tableMasterCheckbox")
        self.toggle_all_checkbox.setToolTip("Marcar o desmarcar todas las categorías visibles")
        self.toggle_all_checkbox.stateChanged.connect(self._toggle_all_visible_categories)
        self.table.horizontalScrollBar().valueChanged.connect(lambda *_args: self._position_header_checkbox())

        self.table.setColumnWidth(0, 48)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 116)
        self.table.setColumnWidth(3, 132)
        self.table.setColumnWidth(4, 220)
        self.table.setColumnWidth(5, 104)
        self.table.setColumnWidth(6, 136)
        self.table.setColumnWidth(7, 108)
        self._position_header_checkbox()

        layout.addLayout(title_row)
        layout.addWidget(self.table)
        return box

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #f5eee4; }
            QLabel { color: #213245; font-size: 15px; }
            QLabel#sectionTitle { color: #111111; font-size: 18px; font-weight: 700; }
            QLabel#summaryCounter { color: #213245; font-size: 16px; font-weight: 700; padding-top: 6px; }
            QGroupBox { border: 1px solid #e4d7c5; border-radius: 16px; background: white; padding: 12px; }
            QGroupBox::title { color: transparent; }
            QScrollArea#summaryScroll {
                background: transparent;
                border: none;
            }
            QScrollArea#summaryScroll > QWidget > QWidget#summaryContent {
                background: transparent;
            }
            QScrollArea#summaryScroll QScrollBar:vertical {
                background: #f7f1e7;
                width: 10px;
                margin: 2px 0 2px 0;
                border-radius: 5px;
            }
            QScrollArea#summaryScroll QScrollBar::handle:vertical {
                background: #d8c8af;
                min-height: 28px;
                border-radius: 5px;
            }
            QScrollArea#summaryScroll QScrollBar::handle:vertical:hover {
                background: #c6b49a;
            }
            QScrollArea#summaryScroll QScrollBar::add-line:vertical,
            QScrollArea#summaryScroll QScrollBar::sub-line:vertical,
            QScrollArea#summaryScroll QScrollBar::add-page:vertical,
            QScrollArea#summaryScroll QScrollBar::sub-page:vertical {
                background: transparent;
                height: 0px;
            }
            QLineEdit, QComboBox, QTableWidget {
                background: white; color: #111111; border: 1px solid #d7cbb8;
                border-radius: 10px; padding: 9px 13px; font-size: 15px;
            }
            QComboBox {
                min-height: 22px; padding-right: 40px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #fbf7f0);
            }
            QComboBox:hover, QLineEdit:hover { border: 1px solid #c6b49a; }
            QComboBox:focus, QLineEdit:focus { border: 1px solid #1d4f91; }
            QComboBox::drop-down {
                subcontrol-origin: padding; subcontrol-position: top right; width: 30px;
                border-left: 1px solid #d7cbb8; background: #f7f1e7;
                border-top-right-radius: 10px; border-bottom-right-radius: 10px;
            }
            QComboBox::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/arrowdown-16.png);
                width: 14px; height: 14px;
            }
            QComboBox QAbstractItemView {
                color: #111111; background: white; font-size: 15px; border: 1px solid #d7cbb8;
                selection-background-color: #e9f0fb; selection-color: #111111;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f6efe3, stop:1 #efe2cc);
                color: #213245; border: none; border-bottom: 1px solid #dfcfb8;
                padding: 10px 8px; font-size: 15px; font-weight: 600; text-align: center;
            }
            QTableWidget { gridline-color: #eadfce; selection-background-color: #dfeafb; selection-color: #111111; }
            QTableCornerButton::section { background: #f7f1e7; border: none; border-bottom: 1px solid #e4d7c5; }
            QCheckBox { background: transparent; }
            QCheckBox::indicator {
                width: 16px; height: 16px; border: 1px solid #7a8594;
                border-radius: 4px; background: #ffffff;
            }
            QCheckBox::indicator:hover { border: 1px solid #4f5f74; }
            QCheckBox::indicator:checked {
                background: #57b7ea; border: 1px solid #57b7ea;
                image: url(:/qt-project.org/styles/commonstyle/images/checkbox_checked.png);
            }
            QPushButton {
                background: #1d4f91; color: white; border: none; border-radius: 12px;
                padding: 12px 16px; font-weight: 700; font-size: 15px;
            }
            QPushButton:hover { background: #163d71; }
            QPushButton:disabled { background: #9fb4d2; color: #eff4fb; }
            QToolTip { color: #111111; background-color: #fffaf2; border: 1px solid #d7cbb8; padding: 8px; }
            """
        )
        QToolTip.setFont(QFont("Segoe UI", 11))

    def refresh_categories(self) -> None:
        self._all_categories = self.service.list_custom_categories()
        self._refresh_group_filter_options()
        self.apply_category_filters()

    def _refresh_group_filter_options(self) -> None:
        current_data = self.filter_group_combo.currentData()
        groups = sorted({item.grupo for item in self._all_categories if item.grupo})

        self.filter_group_combo.blockSignals(True)
        self.filter_group_combo.clear()
        self.filter_group_combo.addItem("Todos", "")
        self.filter_group_combo.addItem("Sin grupo", "__none__")
        for group in groups:
            self.filter_group_combo.addItem(group, group)
        index = self.filter_group_combo.findData(current_data)
        self.filter_group_combo.setCurrentIndex(index if index >= 0 else 0)
        self.filter_group_combo.blockSignals(False)

    def apply_category_filters(self) -> None:
        categories = list(self._all_categories)

        search_text = self.filter_input.text().strip().lower()
        filter_type = self.filter_type_combo.currentData()
        filter_nature = self.filter_nature_combo.currentData()
        filter_group = self.filter_group_combo.currentData()
        filter_essential = self.filter_essential_combo.currentData()
        filter_status = self.filter_status_combo.currentData()
        filter_frequency = self.filter_frequency_combo.currentData()

        if search_text:
            categories = [
                item
                for item in categories
                if search_text in item.nombre.lower()
                or search_text in item.descripcion.lower()
                or search_text in item.grupo.lower()
            ]
        if filter_type:
            categories = [item for item in categories if item.tipo_movimiento == filter_type]
        if filter_nature:
            categories = [item for item in categories if item.naturaleza == filter_nature]
        if filter_group == "__none__":
            categories = [item for item in categories if not item.grupo]
        elif filter_group:
            categories = [item for item in categories if item.grupo == filter_group]
        if filter_essential == "yes":
            categories = [item for item in categories if item.esencial]
        elif filter_essential == "no":
            categories = [item for item in categories if not item.esencial]
        if filter_status == "active":
            categories = [item for item in categories if item.activa]
        elif filter_status == "archived":
            categories = [item for item in categories if not item.activa]
        if filter_frequency == "__none__":
            categories = [item for item in categories if not item.frecuencia]
        elif filter_frequency != "all":
            categories = [item for item in categories if item.frecuencia == filter_frequency]

        categories.sort(
            key=lambda item: self._sort_value(item, self._sort_column),
            reverse=self._sort_descending,
        )
        self._displayed_categories = categories
        self._populate_table(categories)
        self._refresh_summary(filtered_categories=categories)
        self._update_checked_count()
        self._on_selection_changed()

    def _sort_value(self, category: CustomCategory, column: int):
        if column == 1:
            return category.nombre.lower()
        if column == 2:
            return TYPE_LABELS[category.tipo_movimiento].lower()
        if column == 3:
            return NATURE_LABELS[category.naturaleza].lower()
        if column == 4:
            return (category.grupo or "").lower()
        if column == 5:
            return ESSENTIAL_LABELS[category.esencial].lower()
        if column == 6:
            return FREQUENCY_LABELS.get(category.frecuencia, "Sin definir").lower()
        if column == 7:
            return STATUS_LABELS[category.activa].lower()
        return category.nombre.lower()

    def _handle_header_sort(self, section: int) -> None:
        if section == 0:
            return
        if self._sort_column == section:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_column = section
            self._sort_descending = False
        self.apply_category_filters()

    def _populate_table(self, categories: list[CustomCategory]) -> None:
        self.table.setRowCount(len(categories))
        for row, category in enumerate(categories):
            row_color = QColor(self.TYPE_ROW_COLORS.get(category.tipo_movimiento, "#ffffff"))
            if not category.activa:
                row_color = row_color.darker(104)

            self.table.setCellWidget(row, 0, self._build_checkbox_cell(category.id, row_color))
            items = [
                self._make_table_item(category.nombre, row_color),
                self._make_table_item(TYPE_LABELS[category.tipo_movimiento], row_color),
                self._make_table_item(NATURE_LABELS[category.naturaleza], row_color),
                self._make_table_item(category.grupo or "Sin grupo", row_color),
                self._make_table_item(ESSENTIAL_LABELS[category.esencial], row_color),
                self._make_table_item(FREQUENCY_LABELS.get(category.frecuencia, "Sin definir"), row_color),
                self._make_table_item(STATUS_LABELS[category.activa], row_color),
            ]

            tooltip = _category_tooltip(category)
            for column, item in enumerate(items, start=1):
                item.setToolTip(tooltip)
                if not category.activa:
                    font = item.font()
                    font.setItalic(True)
                    item.setFont(font)
                    item.setForeground(QColor("#6b7280"))
                if column == 7 and not category.activa:
                    item.setForeground(QColor("#9a3412"))
                self.table.setItem(row, column, item)

        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(2)
        self.table.resizeColumnToContents(3)
        self.table.resizeColumnToContents(5)
        self.table.resizeColumnToContents(6)
        self.table.resizeColumnToContents(7)

    def _make_table_item(self, text: str, background: QColor) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setBackground(background)
        return item

    def _build_checkbox_cell(self, category_id: int | None, background: QColor) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet(f"background-color: {background.name()}; border: none;")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        checkbox = QCheckBox()
        checkbox.setProperty("category_id", category_id)
        checkbox.stateChanged.connect(self._update_checked_count)

        layout.addStretch(1)
        layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        return wrapper

    def _checked_categories(self) -> list[CustomCategory]:
        selected: list[CustomCategory] = []
        by_id = {item.id: item for item in self._displayed_categories}
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget is None:
                continue
            checkbox = widget.findChild(QCheckBox)
            if checkbox is None or not checkbox.isChecked():
                continue
            category_id = checkbox.property("category_id")
            category = by_id.get(category_id)
            if category is not None:
                selected.append(category)
        return selected

    def _clear_checked_categories(self) -> None:
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget is None:
                continue
            checkbox = widget.findChild(QCheckBox)
            if checkbox is not None and checkbox.isChecked():
                checkbox.setChecked(False)

    def _toggle_all_visible_categories(self) -> None:
        check_all = self.toggle_all_checkbox.isChecked()
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget is None:
                continue
            checkbox = widget.findChild(QCheckBox)
            if checkbox is not None and checkbox.isChecked() != check_all:
                checkbox.setChecked(check_all)

    def _position_header_checkbox(self) -> None:
        header = self.table.horizontalHeader()
        x_pos = header.sectionPosition(0)
        width = header.sectionSize(0)
        height = header.height()
        indicator_size = 18
        x_center = x_pos + max(0, (width - indicator_size) // 2)
        y_center = max(0, (height - indicator_size) // 2)
        self.toggle_all_checkbox.setGeometry(x_center, y_center, indicator_size, indicator_size)
        self.toggle_all_checkbox.raise_()

    def _selected_category(self) -> CustomCategory | None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return None
        row = selected_items[0].row()
        if row < 0 or row >= len(self._displayed_categories):
            return None
        return self._displayed_categories[row]

    def _detail_category(self) -> CustomCategory | None:
        checked_categories = self._checked_categories()
        if len(checked_categories) == 1:
            return checked_categories[0]
        return self._selected_category()

    def _refresh_summary(self, *, filtered_categories: list[CustomCategory]) -> None:
        global_categories = self._all_categories
        total = len(global_categories)
        active_count = sum(1 for item in global_categories if item.activa)
        archived_count = total - active_count
        essential_count = sum(1 for item in global_categories if item.esencial)
        type_counts = Counter(item.tipo_movimiento for item in global_categories)
        nature_counts = Counter(item.naturaleza for item in global_categories)

        self.visible_label.setText(f"<b>Visibles con filtros:</b> {len(filtered_categories)} de {total}")
        self.total_label.setText(f"<b>Total global:</b> {total}")
        self.state_label.setText(f"<b>Estado:</b> activas {active_count} | archivadas {archived_count}")
        self.type_label.setText(
            f"<b>Tipos:</b> ingresos {type_counts['ingreso']} | "
            f"gastos {type_counts['gasto']} | inversiones {type_counts['inversion']}"
        )
        self.nature_label.setText(
            f"<b>Naturaleza:</b> fijas {nature_counts['fijo']} | "
            f"variables {nature_counts['variable']} | inesperadas {nature_counts['inesperado']}"
        )
        self.essential_label.setText(f"<b>Esenciales:</b> sí {essential_count} | no {total - essential_count}")

    def _update_checked_count(self) -> None:
        checked = len(self._checked_categories())
        total = len(self._displayed_categories)
        self.checked_count_label.setText(f"Categorías marcadas: {checked} / {total}")
        self.toggle_all_checkbox.blockSignals(True)
        self.toggle_all_checkbox.setChecked(total > 0 and checked == total)
        self.toggle_all_checkbox.blockSignals(False)
        self.edit_button.setEnabled(checked == 1)
        self.archive_button.setEnabled(checked > 0)
        self.delete_button.setEnabled(checked > 0)
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        category = self._detail_category()

        if category is None:
            self.selected_name_label.setText("Ninguna categoría seleccionada.")
            self.selected_description_label.setText(
                "Descripción: selecciona una fila para ver más detalle."
            )
            self.selected_meta_label.setText("")
            return

        self.selected_name_label.setText(
            f"<b>{category.nombre}</b> · {TYPE_LABELS[category.tipo_movimiento]} · {NATURE_LABELS[category.naturaleza]}"
        )
        self.selected_description_label.setText(
            f"Descripción: {category.descripcion or 'Sin descripción'}"
        )
        self.selected_meta_label.setText(
            f"Grupo: {category.grupo or 'Sin grupo'} | "
            f"Esencial: {ESSENTIAL_LABELS[category.esencial]} | "
            f"Frecuencia: {FREQUENCY_LABELS.get(category.frecuencia, 'Sin definir')} | "
            f"Estado: {STATUS_LABELS[category.activa]}"
        )

    def _show_message(self, title: str, text: str, kind: str = "information") -> QMessageBox.StandardButton:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        if kind == "warning":
            box.setIcon(QMessageBox.Icon.Warning)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
        elif kind == "question":
            box.setIcon(QMessageBox.Icon.Question)
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
        else:
            box.setIcon(QMessageBox.Icon.Information)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)

        yes_button = box.button(QMessageBox.StandardButton.Yes)
        no_button = box.button(QMessageBox.StandardButton.No)
        ok_button = box.button(QMessageBox.StandardButton.Ok)
        if yes_button is not None:
            yes_button.setText("Sí")
        if no_button is not None:
            no_button.setText("No")
        if ok_button is not None:
            ok_button.setText("Aceptar")

        box.setStyleSheet(
            """
            QMessageBox { background: #f5eee4; }
            QMessageBox QLabel { color: #213245; font-size: 15px; }
            QMessageBox QPushButton {
                background: #1d4f91; color: white; border: none; border-radius: 10px;
                padding: 10px 18px; min-width: 96px; font-size: 14px; font-weight: 700;
            }
            QMessageBox QPushButton:hover { background: #163d71; }
            """
        )
        return box.exec()

    def open_new_category_dialog(self) -> None:
        self._clear_checked_categories()
        self.table.clearSelection()
        self._update_checked_count()
        self._on_selection_changed()

        dialog = CategoryEditorDialog(self, title="Nueva categoría")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self.service.create_custom_category(**dialog.payload())
        except ValueError as exc:
            self._show_message("Categoría no válida", str(exc), "warning")
            return

        self.refresh_categories()
        self.category_changed.emit()
        self._show_message("Categoría guardada", "La nueva categoría ya está disponible.", "information")

    def open_edit_category_dialog(self) -> None:
        checked_categories = self._checked_categories()
        if len(checked_categories) != 1:
            self._show_message(
                "Edición no válida",
                "Para editar, debe haber exactamente una categoría marcada.",
                "warning",
            )
            return

        category = checked_categories[0]

        if category.id is None:
            self._show_message("Edición no válida", "La categoría seleccionada no es válida.", "warning")
            return

        dialog = CategoryEditorDialog(self, title="Editar categoría", category=category)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self.service.update_custom_category(category_id=category.id, **dialog.payload())
        except ValueError as exc:
            self._show_message("No se pudo editar", str(exc), "warning")
            return

        self.refresh_categories()
        self.category_changed.emit()
        self._show_message(
            "Categoría editada",
            "La categoría y sus movimientos asociados se han actualizado.",
            "information",
        )

    def toggle_checked_category_status(self) -> None:
        selected = self._checked_categories()
        if not selected:
            self._show_message(
                "Sin categorías marcadas",
                "Marca una o varias categorías para archivar o activar.",
                "warning",
            )
            return

        activated = 0
        archived = 0
        for category in selected:
            if category.id is None:
                continue
            updated = self.service.set_custom_category_status(category.id, activa=not category.activa)
            if updated.activa:
                activated += 1
            else:
                archived += 1

        self.refresh_categories()
        self.category_changed.emit()

        fragments = []
        if archived:
            fragments.append(f"{archived} archivadas")
        if activated:
            fragments.append(f"{activated} activadas")
        self._show_message(
            "Estado actualizado",
            "Se han actualizado las categorías marcadas: " + ", ".join(fragments) + ".",
            "information",
        )

    def delete_checked_categories(self) -> None:
        selected = self._checked_categories()
        if not selected:
            self._show_message(
                "Sin categorías marcadas",
                "Marca una o varias categorías para eliminarlas.",
                "warning",
            )
            return

        message = (
            "Las categorías sin movimientos se eliminarán definitivamente. "
            "Las que tengan histórico se archivarán para conservar la información.\n\n"
            f"Categorías marcadas: {len(selected)}.\n\n¿Deseas continuar?"
        )
        if self._show_message("Eliminar categorías", message, "question") != QMessageBox.StandardButton.Yes:
            return

        deleted = 0
        archived = 0
        for category in selected:
            if category.id is None:
                continue
            try:
                result = self.service.delete_custom_category(category.id)
            except ValueError as exc:
                self._show_message("No se pudo eliminar", str(exc), "warning")
                return
            if result == "deleted":
                deleted += 1
            elif result == "archived":
                archived += 1

        self.refresh_categories()
        self.category_changed.emit()

        fragments = []
        if deleted:
            fragments.append(f"{deleted} eliminadas")
        if archived:
            fragments.append(f"{archived} archivadas por tener movimientos")
        self._show_message(
            "Proceso completado",
            "Resultado: " + ", ".join(fragments) + ".",
            "information",
        )

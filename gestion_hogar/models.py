from gestion_hogar.backend.entities import (
    CATEGORY_TYPES,
    FREQUENCY_TYPES,
    MOVEMENT_TYPES,
    Movement as Transaction,
)


TYPE_LABELS = {
    "ingreso": "Ingreso",
    "gasto": "Gasto",
    "inversion": "Inversion",
}

NATURE_LABELS = {
    "fijo": "Fijo",
    "variable": "Variable",
    "inesperado": "Inesperado",
}

FREQUENCY_LABELS = {
    "": "Sin definir",
    "diaria": "Diaria",
    "semanal": "Semanal",
    "mensual": "Mensual",
    "trimestral": "Trimestral",
    "anual": "Anual",
    "puntual": "Puntual",
}

STATUS_LABELS = {
    True: "Activa",
    False: "Archivada",
}

ESSENTIAL_LABELS = {
    True: "Si",
    False: "No",
}

DEFAULT_SUBCATEGORIES = {
    "ingreso": ["Nomina", "Pension", "Alquiler", "Extra"],
    "gasto": ["Luz", "Comida", "Combustible", "Viajes", "Internet", "Seguro"],
    "inversion": ["ETF", "Fondo indexado", "Ahorro", "Plan de pensiones"],
}

__all__ = [
    "CATEGORY_TYPES",
    "ESSENTIAL_LABELS",
    "FREQUENCY_LABELS",
    "FREQUENCY_TYPES",
    "MOVEMENT_TYPES",
    "NATURE_LABELS",
    "STATUS_LABELS",
    "TYPE_LABELS",
    "Transaction",
]

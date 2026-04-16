from __future__ import annotations

from dataclasses import dataclass


MOVEMENT_TYPES = ("ingreso", "gasto", "inversion")
CATEGORY_TYPES = ("fijo", "variable", "inesperado")
FREQUENCY_TYPES = ("diaria", "semanal", "mensual", "trimestral", "anual", "puntual")


@dataclass(slots=True)
class Movement:
    cantidad: float
    tipo: str
    categoria: str
    subcategoria: str
    fecha: str
    descripcion: str = ""
    id: int | None = None


@dataclass(slots=True)
class MovementSummary:
    ingresos: float
    gastos: float
    inversiones: float

    @property
    def balance(self) -> float:
        return self.ingresos - self.gastos - self.inversiones


@dataclass(slots=True)
class User:
    username: str
    password_hash: str
    id: int | None = None


@dataclass(slots=True)
class CustomCategory:
    nombre: str
    tipo_movimiento: str
    naturaleza: str
    descripcion: str = ""
    grupo: str = ""
    esencial: bool = False
    frecuencia: str = ""
    activa: bool = True
    id: int | None = None

    @property
    def subtipo(self) -> str:
        return self.naturaleza

    @subtipo.setter
    def subtipo(self, value: str) -> None:
        self.naturaleza = value

    @property
    def estado(self) -> str:
        return "activa" if self.activa else "archivada"

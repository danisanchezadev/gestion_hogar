from __future__ import annotations

import hashlib
import json
import sqlite3
import unicodedata
from pathlib import Path

from gestion_hogar.backend.entities import (
    CATEGORY_TYPES,
    FREQUENCY_TYPES,
    MOVEMENT_TYPES,
    CustomCategory,
    Movement,
    MovementSummary,
    User,
)
from gestion_hogar.backend.repository import SQLiteMovementRepository


class FinanceService:
    def __init__(self, repository: SQLiteMovementRepository) -> None:
        self.repository = repository

    def bootstrap(self, legacy_json_path: Path | None = None) -> None:
        self.ensure_default_user()
        self.ensure_default_categories()
        try:
            self.normalize_default_labels()
            self.backfill_existing_categories()
        except Exception:
            pass

        if self.repository.list_movements():
            return

        migrated = self._import_legacy_json(legacy_json_path) if legacy_json_path else False
        if not migrated:
            self.repository.replace_all(self.seed_movements())

    def list_movements(self) -> list[Movement]:
        return self.repository.list_movements()

    def create_movement(
        self,
        *,
        cantidad: float,
        tipo: str,
        categoria: str,
        subcategoria: str,
        fecha: str,
        descripcion: str = "",
    ) -> Movement:
        self._validate_movement(cantidad, tipo, categoria, subcategoria, fecha)
        movement = Movement(
            cantidad=cantidad,
            tipo=tipo,
            categoria=categoria,
            subcategoria=subcategoria.strip(),
            fecha=fecha,
            descripcion=descripcion.strip(),
        )
        return self.repository.add_movement(movement)

    def get_summary(self) -> MovementSummary:
        movements = self.repository.list_movements()
        ingresos = sum(item.cantidad for item in movements if item.tipo == "ingreso")
        gastos = sum(item.cantidad for item in movements if item.tipo == "gasto")
        inversiones = sum(item.cantidad for item in movements if item.tipo == "inversion")
        return MovementSummary(ingresos=ingresos, gastos=gastos, inversiones=inversiones)

    def get_average(self, tipo: str) -> float:
        if tipo not in MOVEMENT_TYPES:
            raise ValueError(f"Tipo no valido: {tipo}")
        values = [item.cantidad for item in self.repository.list_movements() if item.tipo == tipo]
        return sum(values) / len(values) if values else 0.0

    def authenticate_user(self, username: str, password: str) -> bool:
        if not username.strip() or not password:
            return False

        user = self.repository.get_user_by_username(username.strip())
        if user is None:
            return False

        return user.password_hash == self._hash_password(password)

    def ensure_default_user(self) -> User:
        existing = self.repository.get_user_by_username("admin")
        if existing is not None:
            return existing
        return self.repository.add_user("admin", self._hash_password("admin"))

    def ensure_default_categories(self) -> list[CustomCategory]:
        existing = self.repository.list_custom_categories()
        if existing:
            return existing

        defaults = [
            CustomCategory(
                nombre="Nómina",
                descripcion="Ingreso principal periódico procedente del trabajo.",
                tipo_movimiento="ingreso",
                naturaleza="fijo",
                grupo="Ingresos principales",
                esencial=True,
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Pensión",
                descripcion="Ingreso periódico procedente de pensión.",
                tipo_movimiento="ingreso",
                naturaleza="fijo",
                grupo="Ingresos principales",
                esencial=True,
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Alquileres",
                descripcion="Ingresos procedentes del alquiler de una vivienda o propiedad.",
                tipo_movimiento="ingreso",
                naturaleza="fijo",
                grupo="Ingresos patrimoniales",
                esencial=True,
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Extra",
                descripcion="Ingresos extraordinarios o esporádicos no incluidos en la fuente principal.",
                tipo_movimiento="ingreso",
                naturaleza="variable",
                grupo="Ingresos extraordinarios",
            ),
            CustomCategory(
                nombre="Luz",
                descripcion="Factura de electricidad del hogar.",
                tipo_movimiento="gasto",
                naturaleza="fijo",
                grupo="Vivienda",
                esencial=True,
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Internet",
                descripcion="Servicio de internet del hogar.",
                tipo_movimiento="gasto",
                naturaleza="fijo",
                grupo="Vivienda",
                esencial=True,
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Seguro",
                descripcion="Pago de seguros del hogar, vida, salud o vehículo según el uso registrado.",
                tipo_movimiento="gasto",
                naturaleza="fijo",
                grupo="Seguros",
                esencial=True,
            ),
            CustomCategory(
                nombre="Comida",
                descripcion="Gasto en alimentación y compra habitual de comida.",
                tipo_movimiento="gasto",
                naturaleza="variable",
                grupo="Alimentación",
                esencial=True,
                frecuencia="semanal",
            ),
            CustomCategory(
                nombre="Combustible",
                descripcion="Gasto en gasolina o gasóleo para desplazamientos.",
                tipo_movimiento="gasto",
                naturaleza="variable",
                grupo="Transporte",
                esencial=True,
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Viajes",
                descripcion="Gastos relacionados con viajes, escapadas o vacaciones.",
                tipo_movimiento="gasto",
                naturaleza="variable",
                grupo="Ocio",
            ),
            CustomCategory(
                nombre="Avería",
                descripcion="Gasto imprevisto por reparación o incidencia en hogar, vehículo u otros bienes.",
                tipo_movimiento="gasto",
                naturaleza="inesperado",
                grupo="Imprevistos",
                esencial=True,
                frecuencia="puntual",
            ),
            CustomCategory(
                nombre="ETF",
                descripcion="Aportacion periodica a ETF.",
                tipo_movimiento="inversion",
                naturaleza="fijo",
                grupo="Inversion indexada",
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Fondo indexado",
                descripcion="Aportacion a fondo indexado.",
                tipo_movimiento="inversion",
                naturaleza="fijo",
                grupo="Inversion indexada",
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Ahorro",
                descripcion="Traspaso a cuenta o colchón de ahorro.",
                tipo_movimiento="inversion",
                naturaleza="variable",
                grupo="Ahorro",
                frecuencia="mensual",
            ),
            CustomCategory(
                nombre="Oportunidad",
                descripcion="Compra puntual de una oportunidad de inversion.",
                tipo_movimiento="inversion",
                naturaleza="inesperado",
                grupo="Inversion puntual",
                frecuencia="puntual",
            ),
            CustomCategory(
                nombre="Plan de pensiones",
                descripcion="Aportacion a plan de pensiones.",
                tipo_movimiento="inversion",
                naturaleza="variable",
                grupo="Jubilación",
                frecuencia="mensual",
            ),
        ]
        return [self.repository.add_custom_category(item) for item in defaults]

    def list_custom_categories(self, *, active_only: bool | None = None) -> list[CustomCategory]:
        categories = self.repository.list_custom_categories()
        if active_only is True:
            return [item for item in categories if item.activa]
        if active_only is False:
            return [item for item in categories if not item.activa]
        return categories

    def normalize_default_labels(self) -> None:
        replacements = {
            "nomina": "Nómina",
            "pension": "Pensión",
            "averia": "Avería",
        }
        for category in self.repository.list_custom_categories():
            new_name = replacements.get(self._normalize_key(category.nombre))
            if not new_name or new_name == category.nombre:
                continue
            try:
                self.repository.update_custom_category(
                    category.id,
                    nombre=new_name,
                    descripcion=category.descripcion,
                    tipo_movimiento=category.tipo_movimiento,
                    naturaleza=category.naturaleza,
                    grupo=category.grupo,
                    esencial=category.esencial,
                    frecuencia=category.frecuencia,
                    activa=category.activa,
                )
            except Exception:
                continue

    def backfill_existing_categories(self) -> None:
        for category in self.repository.list_custom_categories():
            if category.id is None:
                continue

            mapped = self._mapped_category_metadata(category)
            inferred = self._infer_category_metadata(category)
            legacy_defaults = self._looks_legacy_category(category)

            descripcion = category.descripcion
            naturaleza = category.naturaleza
            grupo = category.grupo
            frecuencia = category.frecuencia
            esencial = category.esencial

            if not descripcion:
                descripcion = mapped.get("descripcion", "") or inferred.get("descripcion", "")
            mapped_naturaleza = mapped.get("naturaleza")
            if (
                isinstance(mapped_naturaleza, str)
                and mapped_naturaleza in CATEGORY_TYPES
                and category.naturaleza != mapped_naturaleza
                and category.naturaleza == "variable"
            ):
                naturaleza = mapped_naturaleza
            if not grupo:
                grupo = mapped.get("grupo", "") or inferred.get("grupo", "")
            if not frecuencia:
                frecuencia = mapped.get("frecuencia", "") or inferred.get("frecuencia", "")
            if not esencial and legacy_defaults:
                if mapped.get("esencial") is True:
                    esencial = True
                elif inferred.get("esencial") is True:
                    esencial = True

            if (
                descripcion == category.descripcion
                and naturaleza == category.naturaleza
                and grupo == category.grupo
                and frecuencia == category.frecuencia
                and esencial == category.esencial
            ):
                continue

            self.repository.backfill_custom_category(
                category.id,
                descripcion=descripcion,
                naturaleza=naturaleza,
                grupo=grupo,
                esencial=esencial,
                frecuencia=frecuencia,
                activa=category.activa,
            )

    def create_custom_category(
        self,
        *,
        nombre: str,
        tipo_movimiento: str,
        naturaleza: str,
        descripcion: str = "",
        grupo: str = "",
        esencial: bool = False,
        frecuencia: str = "",
        activa: bool = True,
    ) -> CustomCategory:
        payload = self._validate_custom_category_payload(
            nombre=nombre,
            tipo_movimiento=tipo_movimiento,
            naturaleza=naturaleza,
            descripcion=descripcion,
            grupo=grupo,
            esencial=esencial,
            frecuencia=frecuencia,
            activa=activa,
        )
        self._ensure_unique_category(
            nombre=payload["nombre"],
            tipo_movimiento=payload["tipo_movimiento"],
            naturaleza=payload["naturaleza"],
            grupo=payload["grupo"],
        )

        try:
            return self.repository.add_custom_category(CustomCategory(**payload))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Ya existe una categoria con el mismo nombre, tipo, naturaleza y grupo.") from exc

    def update_custom_category(
        self,
        *,
        category_id: int,
        nombre: str,
        tipo_movimiento: str,
        naturaleza: str,
        descripcion: str = "",
        grupo: str = "",
        esencial: bool = False,
        frecuencia: str = "",
        activa: bool = True,
    ) -> CustomCategory:
        if category_id <= 0:
            raise ValueError("La categoria seleccionada no es valida.")

        payload = self._validate_custom_category_payload(
            nombre=nombre,
            tipo_movimiento=tipo_movimiento,
            naturaleza=naturaleza,
            descripcion=descripcion,
            grupo=grupo,
            esencial=esencial,
            frecuencia=frecuencia,
            activa=activa,
        )
        self._ensure_unique_category(
            nombre=payload["nombre"],
            tipo_movimiento=payload["tipo_movimiento"],
            naturaleza=payload["naturaleza"],
            grupo=payload["grupo"],
            ignore_category_id=category_id,
        )

        try:
            updated = self.repository.update_custom_category(category_id, **payload)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Ya existe una categoria con el mismo nombre, tipo, naturaleza y grupo.") from exc

        if updated is None:
            raise ValueError("No se ha encontrado la categoria a editar.")
        return updated

    def set_custom_category_status(self, category_id: int, *, activa: bool) -> CustomCategory:
        if category_id <= 0:
            raise ValueError("La categoria seleccionada no es valida.")

        updated = self.repository.set_custom_category_active(category_id, activa)
        if updated is None:
            raise ValueError("No se ha encontrado la categoria seleccionada.")
        return updated

    def delete_custom_category(self, category_id: int) -> str:
        if category_id <= 0:
            raise ValueError("La categoria seleccionada no es valida.")

        category = self.repository.get_custom_category_by_id(category_id)
        if category is None:
            raise ValueError("No se ha encontrado la categoria a eliminar.")

        usage_count = self.repository.count_movements_for_category(category_id)
        if usage_count > 0:
            self.repository.set_custom_category_active(category_id, False)
            return "archived"

        deleted = self.repository.delete_custom_category(category_id)
        if not deleted:
            raise ValueError("No se ha encontrado la categoria a eliminar.")
        return "deleted"

    def _validate_custom_category_payload(
        self,
        *,
        nombre: str,
        tipo_movimiento: str,
        naturaleza: str,
        descripcion: str,
        grupo: str,
        esencial: bool,
        frecuencia: str,
        activa: bool,
    ) -> dict[str, object]:
        cleaned_name = self._clean_text(nombre)
        cleaned_description = self._clean_text(descripcion, preserve_case=True)
        cleaned_group = self._clean_text(grupo)
        cleaned_frequency = frecuencia.strip().lower()

        if not cleaned_name:
            raise ValueError("El nombre de la categoria es obligatorio.")
        if tipo_movimiento not in MOVEMENT_TYPES:
            raise ValueError(f"Tipo de movimiento no valido: {tipo_movimiento}")
        if naturaleza not in CATEGORY_TYPES:
            raise ValueError(f"Naturaleza no valida: {naturaleza}")
        if cleaned_frequency and cleaned_frequency not in FREQUENCY_TYPES:
            raise ValueError(f"Frecuencia no valida: {frecuencia}")

        return {
            "nombre": cleaned_name,
            "descripcion": cleaned_description,
            "tipo_movimiento": tipo_movimiento,
            "naturaleza": naturaleza,
            "grupo": cleaned_group,
            "esencial": bool(esencial),
            "frecuencia": cleaned_frequency,
            "activa": bool(activa),
        }

    def _ensure_unique_category(
        self,
        *,
        nombre: str,
        tipo_movimiento: str,
        naturaleza: str,
        grupo: str,
        ignore_category_id: int | None = None,
    ) -> None:
        normalized_name = self._normalize_key(nombre)
        normalized_group = self._normalize_key(grupo)

        for category in self.repository.list_custom_categories():
            if ignore_category_id is not None and category.id == ignore_category_id:
                continue
            if category.tipo_movimiento != tipo_movimiento:
                continue
            if category.naturaleza != naturaleza:
                continue
            if self._normalize_key(category.nombre) != normalized_name:
                continue
            if self._normalize_key(category.grupo) != normalized_group:
                continue
            raise ValueError(
                "Ya existe una categoria con el mismo nombre, tipo, naturaleza y grupo. "
                "Revisa el nombre o agrupa mejor la categoria."
            )

    def _validate_movement(
        self,
        cantidad: float,
        tipo: str,
        categoria: str,
        subcategoria: str,
        fecha: str,
    ) -> None:
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")
        if tipo not in MOVEMENT_TYPES:
            raise ValueError(f"Tipo no valido: {tipo}")
        if categoria not in CATEGORY_TYPES:
            raise ValueError(f"Categoria no valida: {categoria}")
        if not subcategoria.strip():
            raise ValueError("La subcategoria es obligatoria.")
        if not fecha.strip():
            raise ValueError("La fecha es obligatoria.")

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_key(value: str) -> str:
        collapsed = " ".join(value.strip().lower().split())
        normalized = unicodedata.normalize("NFKD", collapsed)
        return "".join(char for char in normalized if not unicodedata.combining(char))

    @staticmethod
    def _clean_text(value: str, *, preserve_case: bool = False) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            return ""
        return cleaned if preserve_case else cleaned

    def _looks_legacy_category(self, category: CustomCategory) -> bool:
        return (
            not category.descripcion
            and not category.grupo
            and not category.frecuencia
            and not category.esencial
        )

    def _mapped_category_metadata(self, category: CustomCategory) -> dict[str, object]:
        mapping = {
            "alquileres": {
                "descripcion": "Ingresos procedentes del alquiler de una vivienda o propiedad.",
                "grupo": "Ingresos patrimoniales",
                "esencial": True,
                "frecuencia": "mensual",
                "naturaleza": "fijo",
            },
            "extra": {
                "descripcion": "Ingresos extraordinarios o esporádicos no incluidos en la fuente principal.",
                "grupo": "Ingresos extraordinarios",
                "esencial": False,
                "frecuencia": "",
                "naturaleza": "variable",
            },
            "luz": {
                "descripcion": "Factura de electricidad del hogar.",
                "grupo": "Vivienda",
                "esencial": True,
                "frecuencia": "mensual",
                "naturaleza": "fijo",
            },
            "internet": {
                "descripcion": "Servicio de internet del hogar.",
                "grupo": "Vivienda",
                "esencial": True,
                "frecuencia": "mensual",
                "naturaleza": "fijo",
            },
            "seguro": {
                "descripcion": "Pago de seguros del hogar, vida, salud o vehículo según el uso registrado.",
                "grupo": "Seguros",
                "esencial": True,
                "frecuencia": "",
                "naturaleza": "fijo",
            },
            "comida": {
                "descripcion": "Gasto en alimentación y compra habitual de comida.",
                "grupo": "Alimentación",
                "esencial": True,
                "frecuencia": "semanal",
                "naturaleza": "variable",
            },
            "combustible": {
                "descripcion": "Gasto en gasolina o gasóleo para desplazamientos.",
                "grupo": "Transporte",
                "esencial": True,
                "frecuencia": "mensual",
                "naturaleza": "variable",
            },
            "amazon": {
                "descripcion": "Compras realizadas en Amazon para productos variados.",
                "grupo": "Compras",
                "esencial": False,
                "frecuencia": "",
                "naturaleza": "variable",
            },
            "viajes": {
                "descripcion": "Gastos relacionados con viajes, escapadas o vacaciones.",
                "grupo": "Ocio",
                "esencial": False,
                "frecuencia": "",
                "naturaleza": "variable",
            },
            "boda": {
                "descripcion": "Gasto excepcional relacionado con bodas o celebraciones similares.",
                "grupo": "Eventos",
                "esencial": False,
                "frecuencia": "puntual",
                "naturaleza": "inesperado",
            },
            "loteria": {
                "descripcion": "Ingreso ocasional procedente de premios o sorteos.",
                "grupo": "Ingresos extraordinarios",
                "esencial": False,
                "frecuencia": "",
                "naturaleza": "inesperado",
            },
            "coches": {
                "descripcion": "Gastos generales relacionados con vehículo, mantenimiento o uso.",
                "grupo": "Transporte",
                "esencial": True,
                "frecuencia": "",
                "naturaleza": "variable",
            },
            "nomina": {
                "descripcion": "Ingreso principal periódico procedente del trabajo.",
                "grupo": "Ingresos principales",
                "esencial": True,
                "frecuencia": "mensual",
                "naturaleza": "fijo",
            },
            "pension": {
                "descripcion": "Ingreso periódico procedente de pensión.",
                "grupo": "Ingresos principales",
                "esencial": True,
                "frecuencia": "mensual",
                "naturaleza": "fijo",
            },
            "averia": {
                "descripcion": "Gasto imprevisto por reparación o incidencia en hogar, vehículo u otros bienes.",
                "grupo": "Imprevistos",
                "esencial": True,
                "frecuencia": "puntual",
                "naturaleza": "inesperado",
            },
        }
        return mapping.get(self._normalize_key(category.nombre), {})

    def _infer_category_metadata(self, category: CustomCategory) -> dict[str, object]:
        normalized_name = self._normalize_key(category.nombre)
        inferred: dict[str, object] = {"descripcion": "", "grupo": "", "esencial": False, "frecuencia": ""}

        if any(token in normalized_name for token in ("internet", "luz", "agua", "alquiler")):
            inferred["grupo"] = "Vivienda"
            inferred["esencial"] = True
        elif any(token in normalized_name for token in ("coche", "coches", "gasolina", "gasoil", "combustible")):
            inferred["grupo"] = "Transporte"
            inferred["esencial"] = True
        elif any(token in normalized_name for token in ("comida", "supermercado", "alimentacion")):
            inferred["grupo"] = "Alimentación"
            inferred["esencial"] = True
        elif "seguro" in normalized_name:
            inferred["grupo"] = "Seguros"
            inferred["esencial"] = True
        elif category.tipo_movimiento == "ingreso" and any(token in normalized_name for token in ("nomina", "pension")):
            inferred["grupo"] = "Ingresos principales"
            inferred["esencial"] = True
            inferred["frecuencia"] = "mensual"
        elif category.naturaleza == "inesperado":
            inferred["grupo"] = "Imprevistos"
            inferred["frecuencia"] = "puntual"

        return inferred

    def _import_legacy_json(self, legacy_json_path: Path) -> bool:
        if not legacy_json_path.exists():
            return False

        payload = json.loads(legacy_json_path.read_text(encoding="utf-8"))
        movements: list[Movement] = []
        for item in payload.get("transactions", []):
            old_kind = item.get("kind", "expense")
            movements.append(
                Movement(
                    cantidad=item.get("amount", 0.0),
                    tipo="ingreso" if old_kind == "income" else "gasto",
                    categoria="fijo" if old_kind == "income" else "variable",
                    subcategoria=item.get("category", "General"),
                    fecha=item.get("date", ""),
                    descripcion=item.get("note", ""),
                )
            )

        if not movements:
            return False

        self.repository.replace_all(movements)
        return True

    @staticmethod
    def seed_movements() -> list[Movement]:
        return [
            Movement(
                cantidad=2150.0,
                tipo="ingreso",
                categoria="fijo",
                subcategoria="Nomina",
                fecha="2026-03-01",
                descripcion="Salario mensual",
            ),
            Movement(
                cantidad=320.4,
                tipo="gasto",
                categoria="variable",
                subcategoria="Comida",
                fecha="2026-03-03",
                descripcion="Compra semanal",
            ),
            Movement(
                cantidad=142.15,
                tipo="gasto",
                categoria="fijo",
                subcategoria="Luz",
                fecha="2026-03-07",
                descripcion="Factura de suministros",
            ),
            Movement(
                cantidad=75.0,
                tipo="gasto",
                categoria="variable",
                subcategoria="Combustible",
                fecha="2026-03-10",
                descripcion="Repostaje",
            ),
            Movement(
                cantidad=250.0,
                tipo="inversion",
                categoria="fijo",
                subcategoria="ETF",
                fecha="2026-03-12",
                descripcion="Aportacion automatica",
            ),
        ]

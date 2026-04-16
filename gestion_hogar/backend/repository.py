from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path

from gestion_hogar.backend.entities import (
    CATEGORY_TYPES,
    FREQUENCY_TYPES,
    MOVEMENT_TYPES,
    CustomCategory,
    Movement,
    User,
)


class SQLiteMovementRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            self._ensure_movement_table(connection)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                )
                """
            )
            self._ensure_custom_category_table(connection)
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.commit()

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_sql: str,
    ) -> None:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing_columns = {row["name"] for row in rows}
        if column_name in existing_columns:
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    def _ensure_movement_table(self, connection: sqlite3.Connection) -> None:
        table_sql_row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'movimiento'
            """
        ).fetchone()

        if table_sql_row is None:
            connection.execute(
                """
                CREATE TABLE movimiento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cantidad REAL NOT NULL,
                    tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto', 'inversion')),
                    categoria TEXT NOT NULL CHECK (categoria IN ('fijo', 'variable', 'inesperado')),
                    subcategoria TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    descripcion TEXT NOT NULL DEFAULT ''
                )
                """
            )
            return

        self._ensure_column(connection, "movimiento", "descripcion", "TEXT NOT NULL DEFAULT ''")
        table_sql = table_sql_row["sql"] or ""
        if "'inversion'" in table_sql and "'inesperado'" in table_sql:
            return

        connection.execute("ALTER TABLE movimiento RENAME TO movimiento_old")
        connection.execute(
            """
            CREATE TABLE movimiento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cantidad REAL NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto', 'inversion')),
                categoria TEXT NOT NULL CHECK (categoria IN ('fijo', 'variable', 'inesperado')),
                subcategoria TEXT NOT NULL,
                fecha TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            INSERT INTO movimiento (id, cantidad, tipo, categoria, subcategoria, fecha, descripcion)
            SELECT id, cantidad, tipo, categoria, subcategoria, fecha, COALESCE(descripcion, '')
            FROM movimiento_old
            """
        )
        connection.execute("DROP TABLE movimiento_old")

    def _ensure_custom_category_table(self, connection: sqlite3.Connection) -> None:
        table_sql_row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'categoria_personalizada'
            """
        ).fetchone()

        if table_sql_row is None:
            connection.execute(self._custom_category_table_sql())
            return

        self._ensure_column(connection, "categoria_personalizada", "descripcion", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(connection, "categoria_personalizada", "naturaleza", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(connection, "categoria_personalizada", "grupo", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(connection, "categoria_personalizada", "esencial", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(connection, "categoria_personalizada", "frecuencia", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(connection, "categoria_personalizada", "activa", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(connection, "categoria_personalizada", "subtipo", "TEXT NOT NULL DEFAULT ''")

        connection.execute(
            """
            UPDATE categoria_personalizada
            SET descripcion = COALESCE(descripcion, ''),
                naturaleza = COALESCE(NULLIF(naturaleza, ''), subtipo, 'variable'),
                subtipo = COALESCE(NULLIF(subtipo, ''), naturaleza, 'variable'),
                grupo = COALESCE(grupo, ''),
                frecuencia = COALESCE(frecuencia, ''),
                esencial = COALESCE(esencial, 0),
                activa = COALESCE(activa, 1)
            """
        )

        table_sql = (
            connection.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table' AND name = 'categoria_personalizada'
                """
            ).fetchone()["sql"]
            or ""
        )
        snippets = (
            "descripcion",
            "naturaleza",
            "grupo",
            "esencial",
            "frecuencia",
            "'inversion'",
            "'inesperado'",
            "UNIQUE(nombre, tipo_movimiento, naturaleza, grupo)",
        )
        if all(snippet in table_sql for snippet in snippets):
            return

        connection.execute("ALTER TABLE categoria_personalizada RENAME TO categoria_personalizada_old")
        connection.execute(self._custom_category_table_sql())
        connection.execute(
            """
            INSERT INTO categoria_personalizada (
                id,
                nombre,
                descripcion,
                tipo_movimiento,
                naturaleza,
                subtipo,
                grupo,
                esencial,
                frecuencia,
                activa
            )
            SELECT
                id,
                nombre,
                COALESCE(descripcion, ''),
                tipo_movimiento,
                COALESCE(NULLIF(naturaleza, ''), subtipo, 'variable'),
                COALESCE(NULLIF(subtipo, ''), naturaleza, 'variable'),
                COALESCE(grupo, ''),
                COALESCE(esencial, 0),
                COALESCE(frecuencia, ''),
                COALESCE(activa, 1)
            FROM categoria_personalizada_old
            """
        )
        connection.execute("DROP TABLE categoria_personalizada_old")

    def _custom_category_table_sql(self) -> str:
        frequency_values = "', '".join(FREQUENCY_TYPES)
        return f"""
            CREATE TABLE categoria_personalizada (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                tipo_movimiento TEXT NOT NULL CHECK (tipo_movimiento IN ('ingreso', 'gasto', 'inversion')),
                naturaleza TEXT NOT NULL CHECK (naturaleza IN ('fijo', 'variable', 'inesperado')),
                grupo TEXT NOT NULL DEFAULT '',
                esencial INTEGER NOT NULL DEFAULT 0 CHECK (esencial IN (0, 1)),
                frecuencia TEXT NOT NULL DEFAULT '' CHECK (frecuencia IN ('', '{frequency_values}')),
                activa INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1)),
                subtipo TEXT NOT NULL DEFAULT 'variable' CHECK (subtipo IN ('fijo', 'variable', 'inesperado')),
                UNIQUE(nombre, tipo_movimiento, naturaleza, grupo)
            )
        """

    def list_movements(self) -> list[Movement]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, cantidad, tipo, categoria, subcategoria, fecha, descripcion
                FROM movimiento
                ORDER BY fecha DESC, id DESC
                """
            ).fetchall()

        return [
            Movement(
                id=row["id"],
                cantidad=row["cantidad"],
                tipo=row["tipo"],
                categoria=row["categoria"],
                subcategoria=row["subcategoria"],
                fecha=row["fecha"],
                descripcion=row["descripcion"],
            )
            for row in rows
        ]

    def add_movement(self, movement: Movement) -> Movement:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO movimiento (cantidad, tipo, categoria, subcategoria, fecha, descripcion)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    movement.cantidad,
                    movement.tipo,
                    movement.categoria,
                    movement.subcategoria,
                    movement.fecha,
                    movement.descripcion,
                ),
            )
            connection.commit()

        return Movement(
            id=cursor.lastrowid,
            cantidad=movement.cantidad,
            tipo=movement.tipo,
            categoria=movement.categoria,
            subcategoria=movement.subcategoria,
            fecha=movement.fecha,
            descripcion=movement.descripcion,
        )

    def replace_all(self, movements: list[Movement]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM movimiento")
            connection.executemany(
                """
                INSERT INTO movimiento (cantidad, tipo, categoria, subcategoria, fecha, descripcion)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        movement.cantidad,
                        movement.tipo,
                        movement.categoria,
                        movement.subcategoria,
                        movement.fecha,
                        movement.descripcion,
                    )
                    for movement in movements
                ],
            )
            connection.commit()

    def get_user_by_username(self, username: str) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash
                FROM usuario
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

        if row is None:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
        )

    def add_user(self, username: str, password_hash: str) -> User:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO usuario (username, password_hash)
                VALUES (?, ?)
                """,
                (username, password_hash),
            )
            connection.commit()

        return User(id=cursor.lastrowid, username=username, password_hash=password_hash)

    def list_custom_categories(self) -> list[CustomCategory]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    nombre,
                    descripcion,
                    tipo_movimiento,
                    naturaleza,
                    grupo,
                    esencial,
                    frecuencia,
                    activa
                FROM categoria_personalizada
                ORDER BY activa DESC, tipo_movimiento, naturaleza, grupo, nombre
                """
            ).fetchall()

        return [self._row_to_custom_category(row) for row in rows]

    def get_custom_category_by_id(self, category_id: int) -> CustomCategory | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    nombre,
                    descripcion,
                    tipo_movimiento,
                    naturaleza,
                    grupo,
                    esencial,
                    frecuencia,
                    activa
                FROM categoria_personalizada
                WHERE id = ?
                """,
                (category_id,),
            ).fetchone()

        if row is None:
            return None
        return self._row_to_custom_category(row)

    def add_custom_category(self, category: CustomCategory) -> CustomCategory:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO categoria_personalizada (
                    nombre,
                    descripcion,
                    tipo_movimiento,
                    naturaleza,
                    subtipo,
                    grupo,
                    esencial,
                    frecuencia,
                    activa
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category.nombre,
                    category.descripcion,
                    category.tipo_movimiento,
                    category.naturaleza,
                    category.naturaleza,
                    category.grupo,
                    1 if category.esencial else 0,
                    category.frecuencia,
                    1 if category.activa else 0,
                ),
            )
            connection.commit()

        return CustomCategory(
            id=cursor.lastrowid,
            nombre=category.nombre,
            descripcion=category.descripcion,
            tipo_movimiento=category.tipo_movimiento,
            naturaleza=category.naturaleza,
            grupo=category.grupo,
            esencial=category.esencial,
            frecuencia=category.frecuencia,
            activa=category.activa,
        )

    def delete_custom_category(self, category_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM categoria_personalizada
                WHERE id = ?
                """,
                (category_id,),
            )
            connection.commit()
        return cursor.rowcount > 0

    def update_custom_category(
        self,
        category_id: int,
        *,
        nombre: str,
        descripcion: str,
        tipo_movimiento: str,
        naturaleza: str,
        grupo: str,
        esencial: bool,
        frecuencia: str,
        activa: bool,
    ) -> CustomCategory | None:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT
                    id,
                    nombre,
                    descripcion,
                    tipo_movimiento,
                    naturaleza,
                    grupo,
                    esencial,
                    frecuencia,
                    activa
                FROM categoria_personalizada
                WHERE id = ?
                """,
                (category_id,),
            ).fetchone()
            if existing is None:
                return None

            duplicate = connection.execute(
                """
                SELECT id
                FROM categoria_personalizada
                WHERE nombre = ? AND tipo_movimiento = ? AND naturaleza = ? AND grupo = ? AND id <> ?
                """,
                (nombre, tipo_movimiento, naturaleza, grupo, category_id),
            ).fetchone()
            if duplicate is not None:
                raise sqlite3.IntegrityError("Categoria duplicada.")

            connection.execute(
                """
                UPDATE categoria_personalizada
                SET nombre = ?,
                    descripcion = ?,
                    tipo_movimiento = ?,
                    naturaleza = ?,
                    subtipo = ?,
                    grupo = ?,
                    esencial = ?,
                    frecuencia = ?,
                    activa = ?
                WHERE id = ?
                """,
                (
                    nombre,
                    descripcion,
                    tipo_movimiento,
                    naturaleza,
                    naturaleza,
                    grupo,
                    1 if esencial else 0,
                    frecuencia,
                    1 if activa else 0,
                    category_id,
                ),
            )
            matching_movements = connection.execute(
                """
                SELECT id, subcategoria
                FROM movimiento
                WHERE tipo = ? AND categoria = ?
                """,
                (existing["tipo_movimiento"], existing["naturaleza"]),
            ).fetchall()
            expected_name = self._normalize_key(existing["nombre"])
            movement_ids = [
                row["id"]
                for row in matching_movements
                if self._normalize_key(row["subcategoria"]) == expected_name
            ]
            if movement_ids:
                connection.executemany(
                    """
                    UPDATE movimiento
                    SET subcategoria = ?, tipo = ?, categoria = ?
                    WHERE id = ?
                    """,
                    [
                        (nombre, tipo_movimiento, naturaleza, movement_id)
                        for movement_id in movement_ids
                    ],
                )
            connection.commit()

        return CustomCategory(
            id=category_id,
            nombre=nombre,
            descripcion=descripcion,
            tipo_movimiento=tipo_movimiento,
            naturaleza=naturaleza,
            grupo=grupo,
            esencial=esencial,
            frecuencia=frecuencia,
            activa=activa,
        )

    def set_custom_category_active(self, category_id: int, active: bool) -> CustomCategory | None:
        category = self.get_custom_category_by_id(category_id)
        if category is None:
            return None

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE categoria_personalizada
                SET activa = ?
                WHERE id = ?
                """,
                (1 if active else 0, category_id),
            )
            connection.commit()

        category.activa = active
        return category

    def backfill_custom_category(
        self,
        category_id: int,
        *,
        descripcion: str,
        naturaleza: str,
        grupo: str,
        esencial: bool,
        frecuencia: str,
        activa: bool,
    ) -> CustomCategory | None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE categoria_personalizada
                SET descripcion = ?,
                    naturaleza = ?,
                    grupo = ?,
                    esencial = ?,
                    frecuencia = ?,
                    activa = ?,
                    subtipo = ?
                WHERE id = ?
                """,
                (
                    descripcion,
                    naturaleza,
                    grupo,
                    1 if esencial else 0,
                    frecuencia,
                    1 if activa else 0,
                    naturaleza,
                    category_id,
                ),
            )
            connection.commit()
        return self.get_custom_category_by_id(category_id)

    def count_movements_for_category(self, category_id: int) -> int:
        category = self.get_custom_category_by_id(category_id)
        if category is None:
            return 0

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT subcategoria
                FROM movimiento
                WHERE tipo = ? AND categoria = ?
                """,
                (category.tipo_movimiento, category.naturaleza),
            ).fetchall()
        expected_name = self._normalize_key(category.nombre)
        return sum(1 for row in rows if self._normalize_key(row["subcategoria"]) == expected_name)

    @staticmethod
    def _row_to_custom_category(row: sqlite3.Row) -> CustomCategory:
        return CustomCategory(
            id=row["id"],
            nombre=row["nombre"],
            descripcion=row["descripcion"],
            tipo_movimiento=row["tipo_movimiento"],
            naturaleza=row["naturaleza"],
            grupo=row["grupo"],
            esencial=bool(row["esencial"]),
            frecuencia=row["frecuencia"] or "",
            activa=bool(row["activa"]),
        )

    @staticmethod
    def _normalize_key(value: str) -> str:
        collapsed = " ".join((value or "").strip().lower().split())
        normalized = unicodedata.normalize("NFKD", collapsed)
        return "".join(char for char in normalized if not unicodedata.combining(char))

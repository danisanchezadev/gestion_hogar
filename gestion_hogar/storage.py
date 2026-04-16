from pathlib import Path

from gestion_hogar.backend.repository import SQLiteMovementRepository
from gestion_hogar.backend.service import FinanceService


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "finance_data.db"
LEGACY_JSON_FILE = DATA_DIR / "finance_data.json"


class Storage:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DB_FILE
        self.repository = SQLiteMovementRepository(self.path)
        self.service = FinanceService(self.repository)
        self.service.bootstrap(LEGACY_JSON_FILE)

    def list_movements(self):
        return self.service.list_movements()

    def add_transaction(self, transaction) -> None:
        self.service.create_movement(
            cantidad=transaction.cantidad,
            tipo=transaction.tipo,
            categoria=transaction.categoria,
            subcategoria=transaction.subcategoria,
            fecha=transaction.fecha,
            descripcion=getattr(transaction, "descripcion", ""),
        )

    def load(self):
        return self.service

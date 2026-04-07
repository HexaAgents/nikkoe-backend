from app.repositories.receipt import ReceiptRepository
from app.repositories.supplier import SupplierRepository


class SupplierService:
    def __init__(self, repo: SupplierRepository, receipt_repo: ReceiptRepository | None = None):
        self.repo = repo
        self.receipt_repo = receipt_repo or ReceiptRepository()

    def list_suppliers(self, limit: int = 50, offset: int = 0, search: str | None = None):
        return self.repo.find_all(limit, offset, search=search)

    def get_supplier(self, id: int):
        return self.repo.find_by_id(id)

    def get_supplier_receipts(self, supplier_id: int):
        return self.receipt_repo.find_by_supplier_id(supplier_id)

    def create_supplier(self, data: dict):
        return self.repo.create(data)

    def delete_supplier(self, id: int):
        return self.repo.remove(id)

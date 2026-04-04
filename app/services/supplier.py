from app.repositories.supplier import SupplierRepository


class SupplierService:
    def __init__(self, repo: SupplierRepository):
        self.repo = repo

    def list_suppliers(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def create_supplier(self, data: dict):
        return self.repo.create(data)

    def delete_supplier(self, id: str):
        return self.repo.remove(id)

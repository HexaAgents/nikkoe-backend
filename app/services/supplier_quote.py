from app.repositories.supplier_quote import SupplierQuoteRepository


class SupplierQuoteService:
    def __init__(self, repo: SupplierQuoteRepository):
        self.repo = repo

    def create_quote(self, data: dict):
        return self.repo.create(data)

    def delete_quote(self, id: int):
        return self.repo.remove(id)

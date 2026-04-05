from app.errors import NotFoundError
from app.repositories.sale import SaleRepository


class SaleService:
    def __init__(self, repo: SaleRepository):
        self.repo = repo

    def list_sales(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def get_sale(self, id: int):
        sale = self.repo.find_by_id(id)
        if sale is None:
            raise NotFoundError("Sale", str(id))
        return sale

    def get_sale_lines(self, sale_id: int):
        return self.repo.find_lines(sale_id)

    def create_sale(self, sale_data: dict, lines_data: list[dict]):
        return self.repo.create(sale_data, lines_data)

    def void_sale(self, sale_id: int, user_id: int, reason: str):
        return self.repo.void_sale(sale_id, user_id, reason)

from app.errors import NotFoundError
from app.repositories.inventory import InventoryRepository
from app.repositories.item import ItemRepository
from app.repositories.receipt import ReceiptRepository
from app.repositories.sale import SaleRepository
from app.repositories.supplier_quote import SupplierQuoteRepository


class ItemService:
    def __init__(
        self,
        repo: ItemRepository,
        quote_repo: SupplierQuoteRepository,
        inventory_repo: InventoryRepository,
        receipt_repo: ReceiptRepository,
        sale_repo: SaleRepository,
    ):
        self.repo = repo
        self.quote_repo = quote_repo
        self.inventory_repo = inventory_repo
        self.receipt_repo = receipt_repo
        self.sale_repo = sale_repo

    def list_items(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def search_items(self, query: str, limit: int = 50, offset: int = 0):
        return self.repo.search(query, limit, offset)

    def get_item(self, id: int):
        item = self.repo.find_by_id(id)
        if item is None:
            raise NotFoundError("Item", str(id))
        return item

    def get_item_quotes(self, item_id: int):
        return self.quote_repo.find_by_item_id(item_id)

    def get_item_inventory(self, item_id: int):
        return self.inventory_repo.find_by_item_id(item_id)

    def get_item_receipts(self, item_id: int):
        return self.receipt_repo.find_by_item_id(item_id)

    def get_item_sales(self, item_id: int):
        return self.sale_repo.find_by_item_id(item_id)

    def create_item(self, data: dict):
        return self.repo.create(data)

    def update_item(self, id: int, data: dict):
        return self.repo.update(id, data)

    def delete_item(self, id: int):
        return self.repo.remove(id)

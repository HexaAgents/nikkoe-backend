from app.repositories.inventory import InventoryRepository


class InventoryService:
    def __init__(self, repo: InventoryRepository):
        self.repo = repo

    def list_movements(self, limit: int = 50, offset: int = 0):
        return self.repo.find_movements(limit, offset)

    def list_on_hand(self):
        return self.repo.find_on_hand()

    def transfer_stock(self, from_stock_id: int, to_location_id: int, quantity: int, user_id: int | None = None, notes: str | None = None):
        return self.repo.create_transfer(from_stock_id, to_location_id, quantity, user_id, notes)

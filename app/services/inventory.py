from app.repositories.inventory import InventoryRepository


class InventoryService:
    def __init__(self, repo: InventoryRepository):
        self.repo = repo

    def list_movements(self, limit: int = 50, offset: int = 0, search: str | None = None):
        return self.repo.find_movements(limit, offset, search=search)

    def list_on_hand(self):
        return self.repo.find_on_hand()

    def stock_valuation(self):
        return self.repo.stock_valuation()

    def transfer_stock(
        self,
        from_stock_id: int,
        to_location_id: int,
        quantity: int,
        user_id: int | None = None,
        notes: str | None = None,
    ):
        return self.repo.create_transfer(
            from_stock_id,
            to_location_id,
            quantity,
            user_id,
            notes,
        )

    def cross_transfer_stock(
        self,
        from_item_id: int,
        from_location_id: int,
        to_item_id: int,
        to_location_id: int,
        quantity: int,
        user_id: int | None = None,
        notes: str | None = None,
    ):
        return self.repo.create_cross_transfer(
            from_item_id,
            from_location_id,
            to_item_id,
            to_location_id,
            quantity,
            user_id,
            notes,
        )

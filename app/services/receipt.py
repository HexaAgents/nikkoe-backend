from app.errors import NotFoundError
from app.repositories.receipt import ReceiptRepository


class ReceiptService:
    def __init__(self, repo: ReceiptRepository):
        self.repo = repo

    def list_receipts(self, limit: int = 50, offset: int = 0, search: str | None = None, status: str | None = None):
        if search:
            return self.repo.search_by_part_number(search, limit=limit, offset=offset, status=status)
        return self.repo.find_all(limit, offset, status=status)

    def get_receipt(self, id: int):
        receipt = self.repo.find_by_id(id)
        if receipt is None:
            raise NotFoundError("Receipt", str(id))
        return receipt

    def get_receipt_lines(self, receipt_id: int):
        return self.repo.find_lines(receipt_id)

    def create_receipt(self, receipt_data: dict, lines_data: list[dict]):
        return self.repo.create(receipt_data, lines_data)

    def void_receipt(self, receipt_id: int, user_id: int, reason: str):
        return self.repo.void_receipt(receipt_id, user_id, reason)

from app.errors import NotFoundError
from app.repositories.receipt import ReceiptRepository


class ReceiptService:
    def __init__(self, repo: ReceiptRepository):
        self.repo = repo

    def list_receipts(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def get_receipt(self, id: str):
        receipt = self.repo.find_by_id(id)
        if receipt is None:
            raise NotFoundError("Receipt", id)
        return receipt

    def get_receipt_lines(self, receipt_id: str):
        return self.repo.find_lines(receipt_id)

    def create_receipt(self, receipt_data: dict, lines_data: list[dict]):
        return self.repo.create(receipt_data, lines_data)

    def void_receipt(self, receipt_id: str, user_id: str, reason: str):
        return self.repo.void_receipt(receipt_id, user_id, reason)

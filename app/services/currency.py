from app.repositories.currency import CurrencyRepository


class CurrencyService:
    def __init__(self, repo: CurrencyRepository):
        self.repo = repo

    def list_currencies(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

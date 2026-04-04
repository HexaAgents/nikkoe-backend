from app.repositories.category import CategoryRepository


class CategoryService:
    def __init__(self, repo: CategoryRepository):
        self.repo = repo

    def list_categories(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def create_category(self, data: dict):
        return self.repo.create(data)

    def delete_category(self, id: str):
        return self.repo.remove(id)

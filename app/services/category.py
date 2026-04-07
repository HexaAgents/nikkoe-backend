from app.errors import NotFoundError
from app.repositories.category import CategoryRepository
from app.repositories.item import ItemRepository


class CategoryService:
    def __init__(self, repo: CategoryRepository, item_repo: ItemRepository | None = None):
        self.repo = repo
        self.item_repo = item_repo

    def list_categories(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def get_category(self, id: int):
        category = self.repo.find_by_id(id)
        if category is None:
            raise NotFoundError("Category", str(id))
        return category

    def get_category_items(self, category_id: int, limit: int = 5000, offset: int = 0):
        self.get_category(category_id)
        return self.item_repo.find_by_category(category_id, limit, offset)

    def create_category(self, data: dict):
        return self.repo.create(data)

    def delete_category(self, id: int):
        return self.repo.remove(id)

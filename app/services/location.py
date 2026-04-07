from app.errors import NotFoundError
from app.repositories.location import LocationRepository


class LocationService:
    def __init__(self, repo: LocationRepository):
        self.repo = repo

    def list_locations(self, limit: int = 50, offset: int = 0, search: str | None = None):
        return self.repo.find_all(limit, offset, search=search)

    def get_location_items(self, location_id: int):
        location = self.repo.find_by_id(location_id)
        if location is None:
            raise NotFoundError("Location", str(location_id))
        return self.repo.find_items_by_location(location_id)

    def create_location(self, data: dict):
        return self.repo.create(data)

    def delete_location(self, id: int):
        return self.repo.remove(id)

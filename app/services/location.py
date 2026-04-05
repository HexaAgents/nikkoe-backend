from app.repositories.location import LocationRepository


class LocationService:
    def __init__(self, repo: LocationRepository):
        self.repo = repo

    def list_locations(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def create_location(self, data: dict):
        return self.repo.create(data)

    def delete_location(self, id: int):
        return self.repo.remove(id)

from app.repositories.customer import CustomerRepository


class CustomerService:
    def __init__(self, repo: CustomerRepository):
        self.repo = repo

    def list_customers(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

    def create_customer(self, data: dict):
        return self.repo.create(data)

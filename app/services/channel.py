from app.repositories.channel import ChannelRepository


class ChannelService:
    def __init__(self, repo: ChannelRepository):
        self.repo = repo

    def list_channels(self, limit: int = 50, offset: int = 0):
        return self.repo.find_all(limit, offset)

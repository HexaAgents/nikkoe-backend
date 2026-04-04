from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.channel import ChannelRepository
from app.services.channel import ChannelService

repo = ChannelRepository()
service = ChannelService(repo)
router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("/")
def list_channels(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_channels(limit, offset)

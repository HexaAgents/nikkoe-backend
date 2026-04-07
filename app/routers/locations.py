from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.location import LocationRepository
from app.schemas import LocationInput
from app.services.location import LocationService

repo = LocationRepository()
service = LocationService(repo)
router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("/")
def list_locations(
    limit: int = Query(default=5000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_locations(limit, offset, search=search)


@router.get("/{location_id}/items")
def get_location_items(location_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_location_items(location_id)


@router.post("/", status_code=201)
def create_location(body: LocationInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_location(body.model_dump())


@router.delete("/{location_id}")
def delete_location(location_id: int, user: CurrentUser = Depends(get_current_user)):
    service.delete_location(location_id)
    return {"success": True}

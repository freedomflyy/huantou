from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User
from app.schemas.materials import MaterialCatalogResponse
from app.services.material_catalog import load_material_catalog

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=MaterialCatalogResponse)
def get_material_catalog(_: User = Depends(get_current_user)) -> MaterialCatalogResponse:
    return load_material_catalog()

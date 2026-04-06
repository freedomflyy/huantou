from __future__ import annotations

from fastapi import APIRouter
from app.schemas.materials import MaterialCatalogResponse
from app.services.material_catalog import load_material_catalog

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=MaterialCatalogResponse)
def get_material_catalog() -> MaterialCatalogResponse:
    return load_material_catalog()

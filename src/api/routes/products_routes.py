# Hardcoded product catalog for the shopper UI. No DB table — see seed_data.PRODUCTS.

from fastapi import APIRouter, Depends

from src.api.middleware.auth import get_current_user
from src.services.seed_data import list_products

router = APIRouter()


@router.get("")
async def get_products(current_user: dict = Depends(get_current_user)):
    products = list_products()
    return {"status": "success", "data": products, "count": len(products)}

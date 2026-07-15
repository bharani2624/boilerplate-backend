"""Hardcoded product catalog + seed promos for demos and rejection paths.

Products are not a DB table (spec: a handful is fine). Promos are upserted into
Postgres on startup so restarts stay idempotent.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from database.models.promo import Promo, PromoType
from src.store.promo_store import PromoStore

# Catalog: product_id → name + unit_price. Used by cart routes to validate add-to-cart.
PRODUCTS: dict[str, dict] = {
    "mug": {"product_id": "mug", "name": "Ceramic Mug", "unit_price": Decimal("12.00")},
    "tee": {"product_id": "tee", "name": "Cotton T-Shirt", "unit_price": Decimal("25.00")},
    "hoodie": {"product_id": "hoodie", "name": "Hoodie", "unit_price": Decimal("55.00")},
    "sticker": {"product_id": "sticker", "name": "Sticker Pack", "unit_price": Decimal("3.00")},
    "notebook": {"product_id": "notebook", "name": "Notebook", "unit_price": Decimal("9.99")},
    "bottle": {"product_id": "bottle", "name": "Water Bottle", "unit_price": Decimal("18.00")},
}


def get_product(product_id: str) -> Optional[dict]:
    return PRODUCTS.get(product_id)


def list_products() -> list[dict]:
    return [
        {
            "product_id": p["product_id"],
            "name": p["name"],
            "unit_price": str(p["unit_price"]),
        }
        for p in PRODUCTS.values()
    ]


def _seed_promo_defs() -> list[dict]:
    """Four promos covering percent, fixed+min, expired, high min_spend."""
    now = datetime.now(timezone.utc)
    return [
        {
            "code": "SAVE10",
            "type": PromoType.PERCENT.value,
            "value": Decimal("10.00"),
            "min_spend": None,
            "expires_at": None,
            "active": True,
        },
        {
            "code": "FIVEOFF",
            "type": PromoType.FIXED.value,
            "value": Decimal("5.00"),
            "min_spend": Decimal("50.00"),
            "expires_at": None,
            "active": True,
        },
        {
            "code": "EXPIRED",
            "type": PromoType.PERCENT.value,
            "value": Decimal("20.00"),
            "min_spend": None,
            "expires_at": now - timedelta(days=1),
            "active": True,
        },
        {
            "code": "BIGSPEND",
            "type": PromoType.FIXED.value,
            "value": Decimal("15.00"),
            "min_spend": Decimal("200.00"),
            "expires_at": None,
            "active": True,
        },
    ]


async def seed_promos() -> None:
    """Idempotent upsert of demo promos by code."""
    store = PromoStore()
    for defn in _seed_promo_defs():
        await store.upsert(
            code=defn["code"],
            type=defn["type"],
            value=defn["value"],
            min_spend=defn.get("min_spend"),
            expires_at=defn.get("expires_at"),
            active=defn.get("active", True),
        )

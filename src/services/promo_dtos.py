"""Pure data shapes used by the evaluator. Not ORM — stores map models → these.

Keeps evaluate() free of SQLAlchemy so unit tests need no database.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PromoDTO(BaseModel):
    code: str
    type: str
    value: Decimal
    min_spend: Optional[Decimal] = None
    expires_at: Optional[datetime] = None
    active: bool = True


class CartItemDTO(BaseModel):
    product_id: str
    name: str
    unit_price: Decimal
    qty: int = Field(gt=0)


class EvalResult(BaseModel):
    ok: bool
    code: Optional[str] = None
    cart_total: Decimal
    discount: Decimal = Decimal("0")
    final_total: Decimal
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "code": self.code,
            "cart_total": str(self.cart_total),
            "discount": str(self.discount),
            "final_total": str(self.final_total),
            "reason": self.reason,
        }

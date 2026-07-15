# One line in a user's cart. Linked to users via user_id (JWT session subject).
# Composite PK (user_id, product_id): one row per product per cart; qty updates in place.

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel


class CartItem(SQLModel, table=True):
    """A cart line owned by a user. product_id comes from the hardcoded catalog."""

    __tablename__ = "cart_items"
    __table_args__ = {"schema": "public"}

    user_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("public.users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )
    product_id: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    name: str = Field(sa_column=Column(Text, nullable=False))
    unit_price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    qty: int = Field(sa_column=Column(Integer, nullable=False))

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "product_id": self.product_id,
            "name": self.name,
            "unit_price": str(self.unit_price),
            "qty": self.qty,
            "line_total": str(self.unit_price * self.qty),
        }

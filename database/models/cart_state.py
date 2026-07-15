# Per-user cart metadata: currently applied promo code (if any).
# One row per user; stacking is deferred so a single applied_code is enough.

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel


class CartState(SQLModel, table=True):
    """Session cart state keyed by user_id (1:1 with authenticated user)."""

    __tablename__ = "cart_state"
    __table_args__ = {"schema": "public"}

    user_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("public.users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )
    # Soft reference by code text (not FK) so clearing a promo or seed rewrites
    # don't cascade-delete cart state; evaluator re-validates the code on apply/read.
    applied_code: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "applied_code": self.applied_code,
        }

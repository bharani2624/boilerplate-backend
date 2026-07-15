# Promo code table. Domain core of the discount engine — rules are evaluated in
# src/services/promo_evaluator.py; this model is only persistence + seed shape.
# Stretch columns (max_uses, used_count, target_product_id, stackable_group) exist
# in the schema for later work but are never read by the current evaluator.

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class PromoType(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class Promo(SQLModel, table=True):
    """Admin-defined promo code. Codes stored UPPERCASE; lookups are exact match."""

    __tablename__ = "promos"
    __table_args__ = {"schema": "public"}

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    )
    code: str = Field(sa_column=Column(Text, nullable=False, unique=True, index=True))
    type: str = Field(sa_column=Column(Text, nullable=False))  # "percent" | "fixed"
    value: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    min_spend: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default="true"))

    # Stretch — present, unused by evaluator in this build
    max_uses: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    used_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    target_product_id: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    stackable_group: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "code": self.code,
            "type": self.type,
            "value": str(self.value),
            "min_spend": str(self.min_spend) if self.min_spend is not None else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "active": self.active,
            "max_uses": self.max_uses,
            "used_count": self.used_count,
            "target_product_id": self.target_product_id,
            "stackable_group": self.stackable_group,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

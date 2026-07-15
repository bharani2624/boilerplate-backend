# Database access for promos. Codes are always stored and looked up UPPERCASE.

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select

from database.models.promo import Promo
from src.services.promo_dtos import PromoDTO
from src.store.base_store import BaseStore


class PromoStore(BaseStore):
    async def get_by_code(self, code: str) -> Optional[Promo]:
        normalized = (code or "").strip().upper()
        if not normalized:
            return None
        async with self.get_session() as session:
            result = await session.execute(select(Promo).where(Promo.code == normalized))
            return result.scalars().first()

    async def list_all(self) -> List[Promo]:
        async with self.get_session() as session:
            result = await session.execute(select(Promo).order_by(Promo.code))
            return list(result.scalars().all())

    async def upsert(
        self,
        code: str,
        type: str,
        value: Decimal,
        min_spend: Optional[Decimal] = None,
        expires_at: Optional[datetime] = None,
        active: bool = True,
    ) -> Promo:
        normalized = code.strip().upper()
        async with self.get_session() as session:
            result = await session.execute(select(Promo).where(Promo.code == normalized))
            promo = result.scalars().first()
            if promo:
                promo.type = type
                promo.value = value
                promo.min_spend = min_spend
                promo.expires_at = expires_at
                promo.active = active
                promo.updated_at = datetime.utcnow()
            else:
                promo = Promo(
                    code=normalized,
                    type=type,
                    value=value,
                    min_spend=min_spend,
                    expires_at=expires_at,
                    active=active,
                )
            session.add(promo)
            await session.flush()
            await session.refresh(promo)
            return promo

    @staticmethod
    def to_dto(promo: Promo) -> PromoDTO:
        return PromoDTO(
            code=promo.code,
            type=promo.type,
            value=Decimal(str(promo.value)),
            min_spend=Decimal(str(promo.min_spend)) if promo.min_spend is not None else None,
            expires_at=promo.expires_at,
            active=promo.active,
        )

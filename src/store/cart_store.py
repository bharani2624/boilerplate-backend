# Cart persistence scoped by user_id (JWT subject → users.id FK).

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select

from database.models.cart_item import CartItem
from database.models.cart_state import CartState
from src.services.promo_dtos import CartItemDTO
from src.store.base_store import BaseStore


class CartStore(BaseStore):
    def _uid(self, user_id: str) -> uuid.UUID:
        return uuid.UUID(str(user_id))

    async def list_items(self, user_id: str) -> List[CartItem]:
        async with self.get_session() as session:
            result = await session.execute(
                select(CartItem).where(CartItem.user_id == self._uid(user_id))
            )
            return list(result.scalars().all())

    async def upsert_item(
        self,
        user_id: str,
        product_id: str,
        name: str,
        unit_price: Decimal,
        qty: int,
    ) -> CartItem:
        uid = self._uid(user_id)
        async with self.get_session() as session:
            item = await session.get(CartItem, (uid, product_id))
            if item:
                item.qty = qty
                item.name = name
                item.unit_price = unit_price
            else:
                item = CartItem(
                    user_id=uid,
                    product_id=product_id,
                    name=name,
                    unit_price=unit_price,
                    qty=qty,
                )
            session.add(item)
            # Ensure cart_state row exists for this user
            state = await session.get(CartState, uid)
            if not state:
                session.add(CartState(user_id=uid, applied_code=None))
            await session.flush()
            await session.refresh(item)
            return item

    async def remove_item(self, user_id: str, product_id: str) -> bool:
        uid = self._uid(user_id)
        async with self.get_session() as session:
            item = await session.get(CartItem, (uid, product_id))
            if not item:
                return False
            await session.delete(item)
            return True

    async def get_state(self, user_id: str) -> Optional[CartState]:
        async with self.get_session() as session:
            return await session.get(CartState, self._uid(user_id))

    async def set_applied_code(self, user_id: str, code: Optional[str]) -> CartState:
        uid = self._uid(user_id)
        async with self.get_session() as session:
            state = await session.get(CartState, uid)
            if not state:
                state = CartState(user_id=uid, applied_code=code)
            else:
                state.applied_code = code
            session.add(state)
            await session.flush()
            await session.refresh(state)
            return state

    async def clear_applied_code(self, user_id: str) -> CartState:
        return await self.set_applied_code(user_id, None)

    @staticmethod
    def items_to_dtos(items: List[CartItem]) -> list[CartItemDTO]:
        return [
            CartItemDTO(
                product_id=i.product_id,
                name=i.name,
                unit_price=Decimal(str(i.unit_price)),
                qty=i.qty,
            )
            for i in items
        ]

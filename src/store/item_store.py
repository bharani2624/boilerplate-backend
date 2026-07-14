# All database access for the demo Item entity. Why it's here: same reasoning as
# user_store.py — keeps queries out of route handlers — and it's the file to copy
# when adding a new resource's store (see AGENTS.md for the full pattern).
#
# Async: every method is `async def` and awaits its session calls — see user_store.py's
# module comment for why.

from datetime import datetime
from typing import List, Optional

from sqlmodel import select

from database.models.item import Item
from src.store.base_store import BaseStore


class ItemStore(BaseStore):
    async def list_for_user(self, user_id: str) -> List[Item]:
        async with self.get_session() as session:
            result = await session.execute(
                select(Item).where(Item.user_id == user_id).order_by(Item.created_at.desc())
            )
            return list(result.scalars().all())

    async def get_for_user(self, item_id: str, user_id: str) -> Optional[Item]:
        # Fetch by id, then check ownership in Python rather than filtering user_id in
        # the query — this way a wrong-owner lookup and a nonexistent-id lookup return
        # the exact same "not found" (see items_routes.py), which is what we want.
        async with self.get_session() as session:
            item = await session.get(Item, item_id)
            if item and str(item.user_id) == str(user_id):
                return item
            return None

    async def create(self, user_id: str, title: str, description: Optional[str]) -> Item:
        async with self.get_session() as session:
            item = Item(user_id=user_id, title=title, description=description)
            session.add(item)
            await session.flush()
            await session.refresh(item)
            return item

    async def update(
        self, item_id: str, user_id: str, title: Optional[str], description: Optional[str]
    ) -> Optional[Item]:
        async with self.get_session() as session:
            item = await session.get(Item, item_id)
            if not item or str(item.user_id) != str(user_id):
                return None
            # Only overwrite fields that were actually passed — lets the route accept a
            # partial update (e.g. title only, description left as-is).
            if title is not None:
                item.title = title
            if description is not None:
                item.description = description
            # updated_at has no server-side auto-update trigger, so it must be set
            # explicitly on every write path that changes a row.
            item.updated_at = datetime.utcnow()
            session.add(item)
            await session.flush()
            await session.refresh(item)
            return item

    async def delete(self, item_id: str, user_id: str) -> bool:
        async with self.get_session() as session:
            item = await session.get(Item, item_id)
            if not item or str(item.user_id) != str(user_id):
                return False
            await session.delete(item)
            return True

# All database access for the demo Item entity. Why it's here: same reasoning as
# user_store.py — keeps queries out of route handlers — and it's the file to copy
# when adding a new resource's store (see AGENTS.md for the full pattern).

import uuid
from datetime import datetime
from typing import List, Optional

from sqlmodel import select

from database.models.item import Item
from src.store.base_store import BaseStore


class ItemStore(BaseStore):
    def list_for_user(self, user_id: str) -> List[Item]:
        with self.get_session() as session:
            return list(session.exec(select(Item).where(Item.user_id == user_id).order_by(Item.created_at.desc())))

    def get_for_user(self, item_id: str, user_id: str) -> Optional[Item]:
        # Fetch by id, then check ownership in Python rather than filtering user_id in
        # the query — this way a wrong-owner lookup and a nonexistent-id lookup return
        # the exact same "not found" (see items_routes.py), which is what we want.
        with self.get_session() as session:
            item = session.get(Item, item_id)
            if item and str(item.user_id) == str(user_id):
                return item
            return None

    def create(self, user_id: str, title: str, description: Optional[str]) -> Item:
        with self.get_session() as session:
            item = Item(user_id=user_id, title=title, description=description)
            session.add(item)
            session.flush()
            session.refresh(item)
            return item

    def update(self, item_id: str, user_id: str, title: Optional[str], description: Optional[str]) -> Optional[Item]:
        with self.get_session() as session:
            item = session.get(Item, item_id)
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
            session.flush()
            session.refresh(item)
            return item

    def delete(self, item_id: str, user_id: str) -> bool:
        with self.get_session() as session:
            item = session.get(Item, item_id)
            if not item or str(item.user_id) != str(user_id):
                return False
            session.delete(item)
            return True

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
            if title is not None:
                item.title = title
            if description is not None:
                item.description = description
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

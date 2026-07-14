from typing import Optional

from sqlmodel import select

from database.models.user import User
from src.store.base_store import BaseStore


class UserStore(BaseStore):
    def get_by_google_sub(self, google_sub: str) -> Optional[User]:
        with self.get_session() as session:
            return session.exec(select(User).where(User.google_sub == google_sub)).first()

    def get_by_id(self, user_id: str) -> Optional[User]:
        with self.get_session() as session:
            return session.get(User, user_id)

    def upsert_from_google(self, google_sub: str, email: str, name: Optional[str], picture: Optional[str]) -> User:
        with self.get_session() as session:
            user = session.exec(select(User).where(User.google_sub == google_sub)).first()
            if user:
                user.email = email
                user.name = name
                user.picture = picture
            else:
                user = User(google_sub=google_sub, email=email, name=name, picture=picture)
            session.add(user)
            session.flush()
            session.refresh(user)
            return user

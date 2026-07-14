# All database access for the User entity. Why it's here: routes never talk to the DB
# directly — they call methods on this store, which keeps every query for "users" in
# one place instead of scattered across route handlers.
#
# Async: every method is `async def` and awaits its session calls, since the shared
# engine (database/session.py) is an AsyncEngine. Callers must `await` these methods
# and open the session with `async with self.get_session() as session:`.

from typing import Optional

from sqlmodel import select

from database.models.user import User
from src.store.base_store import BaseStore


class UserStore(BaseStore):
    async def get_by_google_sub(self, google_sub: str) -> Optional[User]:
        async with self.get_session() as session:
            result = await session.execute(select(User).where(User.google_sub == google_sub))
            return result.scalars().first()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        async with self.get_session() as session:
            return await session.get(User, user_id)

    async def upsert_from_google(self, google_sub: str, email: str, name: Optional[str], picture: Optional[str]) -> User:
        """Called on every Google login. Looks up by google_sub (the stable id) rather
        than email, then either refreshes that existing row's profile fields or creates
        a new one — so logging in twice never creates two users for the same person."""
        async with self.get_session() as session:
            result = await session.execute(select(User).where(User.google_sub == google_sub))
            user = result.scalars().first()
            if user:
                user.email = email
                user.name = name
                user.picture = picture
            else:
                user = User(google_sub=google_sub, email=email, name=name, picture=picture)
            session.add(user)
            # flush + refresh: get the DB-generated id/timestamps onto `user` before we
            # return it — without this, a brand-new user's `id` could still be the
            # Python-side default rather than what's actually committed.
            await session.flush()
            await session.refresh(user)
            return user

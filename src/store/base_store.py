"""Base class for store classes. Wraps database/session.py's get_session."""

from database.session import get_session


class BaseStore:
    def get_session(self):
        return get_session()

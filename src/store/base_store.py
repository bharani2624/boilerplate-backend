# Shared base class for every store. Why it's here: without it, each store would import
# database.session directly and every one would need to remember the same
# "async with get_session() as session" boilerplate — this just gives them a single
# self.get_session() so the pattern in AGENTS.md has one place to point to.

from database.session import get_session


class BaseStore:
    def get_session(self):
        return get_session()

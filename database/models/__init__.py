# Importing every model here (rather than relying on someone importing them ad hoc
# elsewhere) guarantees they're all registered on SQLModel.metadata before
# create_db_and_tables() runs at startup — otherwise a model whose module was never
# imported would silently never get its table created.

from database.models.user import User
from database.models.item import Item

__all__ = ["User", "Item"]

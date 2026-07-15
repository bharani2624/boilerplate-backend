# Importing every model here guarantees they're registered on SQLModel.metadata
# before create_db_and_tables() runs at startup.

from database.models.user import User
from database.models.promo import Promo, PromoType
from database.models.cart_item import CartItem
from database.models.cart_state import CartState

__all__ = ["User", "Promo", "PromoType", "CartItem", "CartState"]

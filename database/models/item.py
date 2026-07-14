# Demo CRUD entity. Why it's here: it exists purely to prove the auth + CRUD wiring works
# end-to-end (model -> store -> route -> frontend) so you have a working reference to copy
# when you build your real domain model during the builder round. Delete this file (and
# item_store.py / items_routes.py / ItemsPanel.tsx) once you no longer need the example.

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class Item(SQLModel, table=True):
    """Demo CRUD entity, owned by a user. Replace with your real domain model."""

    __tablename__ = "items"
    __table_args__ = {"schema": "public"}

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    )
    # Foreign key to the owning user — every query in item_store.py filters on this so one
    # user can never read/edit/delete another user's rows.
    user_id: uuid.UUID = Field(foreign_key="public.users.id", index=True)
    title: str
    description: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
    )

    def to_dict(self) -> dict:
        """JSON-safe representation for API responses (UUID/datetime aren't JSON-serializable as-is)."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

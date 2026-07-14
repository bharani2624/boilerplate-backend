# Table definition for authenticated users. Why it's here: Google OAuth only proves who
# someone is — we still need our own row per person to attach app data to (see Item.user_id)
# and to mint our own JWT (which embeds this row's id, not Google's).

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """A user authenticated via Google OAuth."""

    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    # UUID primary key, generated in Python (default_factory) so it's available immediately
    # after construction, with a matching Postgres-side default (server_default) as a
    # backstop for rows inserted by anything other than this SQLModel class.
    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    )
    # Google's "sub" claim: a stable, unique id for the Google account that never changes,
    # unlike email (which a user could theoretically change on Google's side). This is
    # what upsert_from_google() matches on to find an existing user on repeat logins.
    google_sub: str = Field(index=True, unique=True, description="Google's stable subject id for this account")
    email: str = Field(index=True, unique=True)
    name: Optional[str] = Field(default=None)
    picture: Optional[str] = Field(default=None)

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
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

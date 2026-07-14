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

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    )
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
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

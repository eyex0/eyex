from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    settings: Mapped[str | None] = mapped_column(Text, nullable=True)

    members = relationship("OrganizationMember", back_populates="organization", lazy="selectin")


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="member")

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organizations")

from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Numeric
from app.dbtypes import GUID
import uuid
from decimal import Decimal
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    usd_balance = Column(Numeric(precision=20, scale=8), nullable=False, default=Decimal(0))

    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    strategy = relationship("Strategy", back_populates="user", uselist=False, cascade="all, delete-orphan")
    user_roles = relationship("UserRole", foreign_keys="[UserRole.user_id]", back_populates="user", cascade="all, delete-orphan")

    @property
    def roles(self) -> list[str]:
        """Get list of role names for this user"""
        return [ur.role.name for ur in self.user_roles if ur.role]
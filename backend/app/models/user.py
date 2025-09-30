from sqlalchemy.orm import relationship
from sqlalchemy import Column, String
from app.dbtypes import GUID
import uuid
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)

    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
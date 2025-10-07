#!/usr/bin/env python3
"""Create database tables manually"""

from app.database import engine
from app.models.base import Base

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")










# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from app.core.config import settings
# from app.db.base import Base  # Import the central Base

# # Safety check for the URL
# if not settings.DATABASE_URL:
#     raise ValueError("DATABASE_URL is not set!")

# engine = create_engine(
#     settings.DATABASE_URL, 
#     pool_pre_ping=True,
#     # This helps debug connection issues in logs
#     echo=False 
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base

# Read directly from environment - don't use settings
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ FATAL: DATABASE_URL environment variable is not set!")

print(f"✅ DATABASE_URL found: {DATABASE_URL[:30]}...")

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    echo=False 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
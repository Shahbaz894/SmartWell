# # app/db/session.py
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# from app.core.config import settings

# engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base import Base  # Import the central Base

# Safety check for the URL
if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL is not set!")

engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True,
    # This helps debug connection issues in logs
    echo=False 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
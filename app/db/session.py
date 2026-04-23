

# import os
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from app.db.base import Base
# from dotenv import load_dotenv  # <-- Add this


# # Load the .env file from the root directory
# load_dotenv()
# # Read directly from environment - don't use settings
# DATABASE_URL = os.getenv("DATABASE_URL")

# if not DATABASE_URL:
#     raise ValueError("❌ FATAL: DATABASE_URL environment variable is not set!")

# print(f"✅ DATABASE_URL found: {DATABASE_URL[:30]}...")

# engine = create_engine(
#     DATABASE_URL, 
#     pool_pre_ping=True,
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
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
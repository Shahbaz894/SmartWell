# import os
# from pathlib import Path
# from pydantic_settings import BaseSettings, SettingsConfigDict
# from pydantic import field_validator

# # 1. Calculate the path to E:\SmartWell\.env
# # __file__ is E:\SmartWell\app\core\config.py
# # .parent is E:\SmartWell\app\core\
# # .parent.parent is E:\SmartWell\app\
# # .parent.parent.parent is E:\SmartWell\ (The Root)
# root_dir = Path(__file__).resolve().parent.parent.parent
# env_path = root_dir / ".env"

# class Settings(BaseSettings):
#     # This MUST be in your .env file
#     DATABASE_URL: str 
    
#     JWT_SECRET_KEY: str = "YOUR_SECRET_KEY_CHANGE_ME"
#     JWT_ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
#     @field_validator("DATABASE_URL", mode="before")
#     @classmethod
#     def fix_postgres_name(cls, v: str) -> str:
#         if v and v.startswith("postgres://"):
#             return v.replace("postgres://", "postgresql://", 1)
#         return v
    
#     # 2. Tell Pydantic to use the absolute root path
#     model_config = SettingsConfigDict(
#         env_file=env_path, 
#         env_file_encoding="utf-8",
#         extra="ignore"
#     )

# # 3. Instantiate settings
# settings = Settings()
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = "YOUR_SECRET_KEY_CHANGE_ME"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_name(cls, v: str) -> str:
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    
    # We tell Pydantic: "Try to find .env, but if it's not there, don't crash."
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore",
        env_file_required=False  # THIS IS THE IMPORTANT LINE
    )

settings = Settings()
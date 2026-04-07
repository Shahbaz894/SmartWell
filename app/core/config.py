# # app/core/config.py
# # app/core/config.py
# import os
# from pathlib import Path
# from dotenv import load_dotenv
# from pydantic_settings import BaseSettings  # <-- changed

# # Load .env
# env_path = Path(__file__).parent.parent / ".env"
# load_dotenv(dotenv_path=env_path)


# class Settings(BaseSettings):
#     DATABASE_URL: str = os.getenv("DATABASE_URL")
#     JWT_SECRET_KEY: str = "YOUR_SECRET_KEY"
#     JWT_ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

#     class Config:
#         env_file = ".env"


# settings = Settings()

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    # Pydantic will automatically look for a DATABASE_URL env var
    DATABASE_URL: str = "" 
    JWT_SECRET_KEY: str = "YOUR_SECRET_KEY_CHANGE_ME"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # This validator automatically fixes the Railway/Heroku 'postgres' prefix issue
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_name(cls, v: str) -> str:
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # Prevents crashing if Railway adds extra variables
    )

settings = Settings()
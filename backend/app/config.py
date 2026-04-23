from functools import lru_cache
from pydantic import BaseModel
from dotenv import load_dotenv
import os


load_dotenv()


class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "development")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/hcp_crm")


@lru_cache
def get_settings() -> Settings:
    return Settings()

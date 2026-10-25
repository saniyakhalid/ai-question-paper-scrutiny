import os
import secrets
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Based Intelligent Question Paper Scrutiny Decision Support System"
    PROJECT_TITLE: str = "AI-Based Intelligent Question Paper Scrutiny Decision Support System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api"
    
    # Security
    # A random per-process key keeps local development usable without a committed secret.
    # Deployments must set JWT_SECRET to a persistent value in their secret store.
    JWT_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    JWT_ALGORITHM: str = "HS256"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock")  # 'gemini' or 'mock'
    
    # Directory Anchors
    _BACKEND_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _DEFAULT_DB_PATH: str = os.path.join(_BACKEND_DIR, "scrutiny.db")
    _DEFAULT_DB_URL: str = f"sqlite:///{_DEFAULT_DB_PATH.replace(os.sep, '/')}"
    _DEFAULT_UPLOAD_DIR: str = os.path.join(_BACKEND_DIR, "uploads")

    # MongoDB Configuration
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "question_paper_scrutiny")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)
    
    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", _DEFAULT_UPLOAD_DIR)
    MAX_UPLOAD_SIZE_MB: int = 10

    model_config = {"env_file": ".env", "extra": "allow"}

    @property
    def SECRET_KEY(self) -> str:
        """Compatibility alias used by the existing JWT dependency."""
        return self.JWT_SECRET

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if len(self.JWT_SECRET) < 32:
            raise ValueError("Set JWT_SECRET to a generated value of at least 32 characters")
        return self

    def get_database_url(self) -> str:
        url = self.DATABASE_URL or ""
        if url.startswith("sqlite:///") and (url.endswith("./scrutiny.db") or url.endswith("/scrutiny.db")):
            canonical_db = os.path.abspath(os.path.join(self._BACKEND_DIR, "scrutiny.db"))
            return f"sqlite:///{canonical_db.replace(os.sep, '/')}"
        return url

settings = Settings()

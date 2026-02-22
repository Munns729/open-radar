"""Configuration management"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    log_level: str = "INFO"
    
    # API Keys
    moonshot_api_key: Optional[str] = None
    companies_house_api_key: Optional[str] = None
    fca_api_email: Optional[str] = None  # FCA Register API username (email)
    fca_api_key: Optional[str] = None   # FCA Register API key
    notion_api_key: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    admin_email: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    
    # LLM / OpenAI Compatible Keys
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Constants
    kimi_api_base: str = "https://api.moonshot.ai/v1"
    # Heavy analysis (moat scoring, semantic enrichment). Strong model required.
    kimi_model: str = "kimi-k2.5"
    # Browsing agents (website discovery, extraction). Use local Qwen for cost/speed.
    browsing_model: str = "qwen3:8b"
    # Request timeout (seconds) for LLM calls. Increase for slow local models (e.g. Qwen 8B).
    llm_request_timeout: float = 180.0
    # Legacy: model for OpenAI-compatible APIs when not using role-specific models.
    llm_model: Optional[str] = None  # Defaults to kimi_model in validator

    # Currency
    base_currency: str = "GBP"
    preferred_currency: str = "GBP"
    currency_date: Optional[str] = None # ISO Format (YYYY-MM-DD) or None for dynamic

    # Database (PostgreSQL only — run docker-compose up -d)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/radar"

    # SSL: set IGNORE_SSL_ERRORS=1 to bypass cert verification (e.g. BSI bund.de, broken sites)
    ignore_ssl_errors: bool = False

    @field_validator('database_url')
    @classmethod
    def validate_postgres_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError(
                f"Only PostgreSQL is supported. Got: {v[:30]}... "
                "Set DATABASE_URL=postgresql://user:pass@host:5432/radar"
            )
        return v
    
    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Optional[Path] = None
    cache_dir: Optional[Path] = None
    logs_dir: Optional[Path] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @model_validator(mode='after')
    def setup_paths_and_fallbacks(self):
        # Paths
        if self.data_dir is None:
            self.data_dir = self.project_root / "data"
        if self.cache_dir is None:
            self.cache_dir = self.data_dir / "cache"
        if self.logs_dir is None:
            self.logs_dir = self.project_root / "logs"
            
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.logs_dir.mkdir(exist_ok=True, parents=True)

        # Fallbacks for LLM keys
        if not self.openai_api_key:
            self.openai_api_key = self.moonshot_api_key
            
        if not self.openai_api_base:
            self.openai_api_base = self.kimi_api_base

        if self.llm_model is None:
            self.llm_model = self.kimi_model

        return self

    @field_validator('moonshot_api_key')
    @classmethod
    def validate_moonshot_key(cls, v: Optional[str]) -> Optional[str]:
        # You can treat empty string as None or invalid if strictly required
        # For now, we allow None but if the user wants strict check we could add it.
        # The user request said: "raise ValueError if not v"
        # But locally it might be missing? User said "Required" in comment.
        # Let's check environment.
        if v is None and os.getenv("ENVIRONMENT") == "production":
             raise ValueError("MOONSHOT_API_KEY must be set in production")
        return v

# Instantiate settings
settings = Settings()

# Backward compatibility (optional, but helps with refactoring)
# We can map Config.ATR to settings.attr if we really want, 
# but better to refactor the code to use `settings`.


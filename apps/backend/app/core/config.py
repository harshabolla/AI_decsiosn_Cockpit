"""
Core application configuration via environment variables.
All provider config lives here. Agents read from settings only.
NEVER log or print API keys.
"""
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_SECRET_KEY: str = "change-me"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── OpenAI ───────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_FAST_MODEL: str = "gpt-4o-mini"

    # ── Anthropic ─────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"

    # ── Google Gemini ─────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""  # alias for GOOGLE_API_KEY
    GEMINI_DEFAULT_MODEL: str = "gemini-1.5-flash"

    # ── xAI Grok ──────────────────────────────────────────────────────────────
    XAI_API_KEY: str = ""
    GROK_DEFAULT_MODEL: str = "grok-beta"

    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # ── Default Provider ──────────────────────────────────────────────────────
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_LLM_MODEL: str = "gpt-4o"

    # Backward compat
    LLM_PRIMARY_PROVIDER: str = "openai"
    LLM_FALLBACK_PROVIDER: str = "openai"

    # ── Task-Specific Provider Routing ────────────────────────────────────────
    # Each task can be routed to a different provider without changing agent code.
    # If not set, falls back to DEFAULT_LLM_PROVIDER/DEFAULT_LLM_MODEL.
    INTENT_PROVIDER: str = ""
    INTENT_MODEL: str = ""

    SQL_PROVIDER: str = ""
    SQL_MODEL: str = ""

    RAG_PROVIDER: str = ""
    RAG_MODEL: str = ""

    REVIEWER_PROVIDER: str = ""
    REVIEWER_MODEL: str = ""

    FAST_PROVIDER: str = ""
    FAST_MODEL: str = ""

    # Fallback chain (comma-separated): e.g. "anthropic,gemini,grok"
    LLM_FALLBACK_CHAIN: str = ""

    # ── Warehouse ─────────────────────────────────────────────────────────────
    WAREHOUSE_ADAPTER: Literal["local", "snowflake"] = "local"
    SNOWFLAKE_ACCOUNT: str = ""
    SNOWFLAKE_USER: str = ""
    SNOWFLAKE_PASSWORD: str = ""
    SNOWFLAKE_DATABASE: str = ""
    SNOWFLAKE_SCHEMA: str = ""
    SNOWFLAKE_WAREHOUSE: str = ""
    SNOWFLAKE_ROLE: str = ""

    # ── Vector Store ──────────────────────────────────────────────────────────
    VECTOR_STORE: str = "local"  # local | chroma | faiss
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "opella_knowledge"

    # ── ServiceNow ────────────────────────────────────────────────────────────
    SERVICENOW_ADAPTER: Literal["real", "mock"] = "mock"
    SERVICENOW_INSTANCE: str = ""
    SERVICENOW_USERNAME: str = ""
    SERVICENOW_PASSWORD: str = ""

    # ── Security ──────────────────────────────────────────────────────────────
    PII_DETECTION_ENABLED: bool = True
    PROMPT_INJECTION_DETECTION_ENABLED: bool = True
    DLP_ENABLED: bool = True

    # ── Observability ─────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    ENABLE_REQUEST_LOGGING: bool = True

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 30

    # ── Memory ────────────────────────────────────────────────────────────────
    CONVERSATION_MEMORY_ENABLED: bool = True
    CONVERSATION_MEMORY_MAX_TURNS: int = 10


settings = Settings()

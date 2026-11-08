from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Job Hunter"
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://jobhunter:jobhunter@localhost:5432/ai_job_hunter"
    redis_url: str = "redis://localhost:6379/0"

    default_user_email: str = "abdulwasay@example.com"
    default_user_name: str = "Abdul Wasay"

    # App login (required for deploy). Only these emails can sign in with Google,
    # and/or AUTH_PASSWORD for password login.
    auth_password: str = ""
    allowed_login_emails: str = ""
    auth_disabled: bool = False
    session_max_age_hours: int = 168  # 7 days

    token_encryption_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    google_sheets_title: str = "AI Job Hunter - Abdul Wasay"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    google_generative_ai_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    serpapi_api_key: str = ""

    @property
    def effective_gemini_key(self) -> str:
        return self.gemini_api_key or self.google_generative_ai_api_key


    google_scopes: List[str] = Field(
        default_factory=lambda: [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/drive.file",
            # Needed to download existing Drive CV links the user pastes in
            "https://www.googleapis.com/auth/drive.readonly",
        ]
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_login_email_list(self) -> List[str]:
        raw = (self.allowed_login_emails or "").strip()
        if not raw:
            return [self.default_user_email.strip().lower()] if self.default_user_email else []
        return [e.strip().lower() for e in raw.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

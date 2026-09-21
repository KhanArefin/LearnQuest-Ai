"""Application settings. SHARED FILE - change only by agreement (plan.md 2.4)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- app ---
    app_env: str = "development"
    # Vite falls back to 5174/5175 when 5173 is taken (a second dev server,
    # a stray process). Allowing the fallbacks avoids every request failing
    # CORS preflight just because the frontend moved port.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175"

    # --- database (M3) ---
    database_url: str = ""

    # --- auth: Supabase Auth (M3) ---
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""
    dev_allow_anonymous: bool = True
    jwt_leeway_seconds: int = 7200

    # --- llm (M1) ---
    llm_provider: str = "mock"
    llm_api_key: str = ""
    # Gemini 2.5+ are "thinking" models: internal reasoning is billed against
    # maxOutputTokens, so a small cap leaves nothing for the visible answer
    # (measured: 237 of 250 tokens went to thinking, answer truncated at 31
    # chars). 0 disables thinking; raise it only if you also raise max_tokens.
    llm_thinking_budget: int = 0
    llm_model: str = "llama-3.3-70b-versatile"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2

    # --- avatar (M1) ---
    avatar_service_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_ANON_KEY: str
    PORT: int = 3000
    CORS_ORIGINS: str = "http://localhost:8080"

    OPENAI_API_KEY: str = ""

    EBAY_CLIENT_ID: str = ""
    EBAY_CLIENT_SECRET: str = ""
    EBAY_RU_NAME: str = ""
    EBAY_ENVIRONMENT: str = "SANDBOX"
    EBAY_SYNC_INTERVAL_MINUTES: int = 15

    class Config:
        env_file = ".env"


settings = Settings()

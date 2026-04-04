from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_ANON_KEY: str
    PORT: int = 3000
    CORS_ORIGINS: str = "http://localhost:8080"

    class Config:
        env_file = ".env"


settings = Settings()

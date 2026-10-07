from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    secret_key: str = "change-me"
    access_token_minutes: int = 60 * 8
    cookie_secure: bool = False
    upload_dir: str = "./uploads"
    max_upload_mb: int = 20
    auto_create_tables: bool = True
    admin_email: str = "admin@example.com"
    admin_password: str = "admin12345"
    admin_name: str = "Admin"


settings = Settings()

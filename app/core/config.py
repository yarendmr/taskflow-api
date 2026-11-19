
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application settings
    app_name: str = "TaskFlow API"
    app_description: str = (
        "Kullanıcı, proje ve görev yönetimi için REST API"
    )
    app_version: str = "0.1.0"

    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "taskflow_db"
    db_user: str = "taskflow_user"
    db_password: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

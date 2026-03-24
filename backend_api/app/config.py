from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # MongoDB
    mongodb_url: str = "mongodb://mongo:27017"
    mongodb_db_name: str = "west_end_glass"

    # Meta Cloud API (WhatsApp)
    meta_whatsapp_token: str
    meta_phone_number_id: str
    meta_verify_token: str
    meta_app_secret: str

    # Anthropic Claude
    anthropic_api_key: str

    # Admin JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Admin seed credentials
    admin_username: str = "admin"
    admin_password: str

    # File storage
    photo_storage_path: str = "/data/photos"

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

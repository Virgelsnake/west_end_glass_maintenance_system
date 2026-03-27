from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # MongoDB
    mongodb_url: str = "mongodb://mongo:27017"
    mongodb_db_name: str = "west_end_glass"

    # Meta Cloud API (WhatsApp)
    meta_app_id: str = ""
    meta_whatsapp_token: str
    meta_phone_number_id: str
    meta_verify_token: str
    meta_app_secret: str
    meta_waba_id: str = ""  # WhatsApp Business Account ID
    whatsapp_business_number: str = ""  # digits only e.g. 447700900123 — used in QR/NFC deep links
    west_end_call_back_url: str = ""
    west_end_call_back_token: str = ""

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
        extra = "ignore"


settings = Settings()

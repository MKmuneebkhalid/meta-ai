from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Meta API Credentials
    meta_app_id: str
    meta_app_secret: str
    meta_access_token: str
    meta_ad_account_id: str
    
    # Database
    database_url: str = "sqlite:///./meta_ai_analyst.db"
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    
    # Application
    environment: str = "development"
    api_port: int = int(os.getenv("PORT", 8000))  # Use PORT from Render
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

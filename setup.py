"""Database setup script."""

from app.database import engine, Base
from app.config import settings

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database setup complete!")
    print(f"\nConfiguration:")
    print(f"  Environment: {settings.environment}")
    print(f"  API Port: {settings.api_port}")
    print(f"  Ad Account ID: {settings.meta_ad_account_id}")

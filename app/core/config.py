from pydantic_settings import BaseSettings, SettingsConfigDict

# from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    API_VERSION: str = "v6.2.0"
    DATABASE_URL: str = "sqlite:///./app.db"

    JWT_ISSUER: str = "mh-screening"
    JWT_AUDIENCE: str = "mh-screening-mobile"
    JWT_ACCESS_TTL_SECONDS: int = 3600
    JWT_REFRESH_TTL_DAYS: int = 14
    JWT_SECRET: str = "change_me_super_secret"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT_SECONDS: int = 25

    # Google / Firebase sign-in (recommended: verify Firebase ID token from client)
    GOOGLE_CLIENT_ID: str = ""  # Web/Android client ID used to verify Google ID tokens
    FIREBASE_PROJECT_ID: str = ""  # optional; enables Firebase ID token verification
    # If set, should be the *contents* of a Firebase service account JSON.
    # Use a secrets manager in production.
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    # Cloudinary image uploads
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_FOLDER: str = "mh-screening"


    ALLOW_DEV_DEBUG_META: bool = True

   # 🔑 THIS IS WHAT YOU WERE MISSING
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

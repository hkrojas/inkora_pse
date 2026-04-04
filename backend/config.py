import os

from pydantic_settings import BaseSettings, SettingsConfigDict


_DEV_SECRET_FALLBACK = "dev-only-insecure-secret-key-change-me"
_DEV_DATABASE_FALLBACK = "postgresql://user:password@localhost/dbname"


class Settings(BaseSettings):
    APP_ENV: str = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()

    # Base de Datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", _DEV_DATABASE_FALLBACK)

    # Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    INTERNAL_REGISTRATION_TOKEN: str = os.getenv("INTERNAL_REGISTRATION_TOKEN", "")

    # Facturación y APIs Externas (APIsPERU)
    API_URL: str = os.getenv("API_URL", "https://facturacion.apisperu.com/api/v1")
    API_TOKEN: str = os.getenv("API_TOKEN", "")

    # Consulta DNI/RUC (APIsPERU)
    DNIRUC_API_URL: str = os.getenv("DNIRUC_API_URL", "https://dniruc.apisperu.com/api/v1")
    DNIRUC_TOKEN: str = os.getenv("DNIRUC_TOKEN", "")

    # Inteligencia Artificial (Google Gemini)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Supabase (Cloud Storage y Auth)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # URL del Backend para enlaces públicos (Fase 3)
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def model_post_init(self, __context) -> None:
        is_production = self.APP_ENV in {"production", "prod"}

        if not self.SECRET_KEY:
            if is_production:
                raise ValueError("SECRET_KEY es obligatoria en producción.")
            object.__setattr__(self, "SECRET_KEY", _DEV_SECRET_FALLBACK)

        if is_production and self.SECRET_KEY == _DEV_SECRET_FALLBACK:
            raise ValueError("SECRET_KEY insegura en producción.")

        if is_production and (
            not self.DATABASE_URL or self.DATABASE_URL == _DEV_DATABASE_FALLBACK
        ):
            raise ValueError("DATABASE_URL válida es obligatoria en producción.")


settings = Settings()

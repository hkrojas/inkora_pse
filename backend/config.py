from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_LOCAL_ENVIRONMENTS = {"local", "development", "dev", "test"}
_VALID_FISCAL_ENVIRONMENTS = {"beta", "production"}
_DEFAULT_LOCAL_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]
_DEFAULT_REMOTE_CORS_ORIGINS = [
    "https://inkora-pse.vercel.app",
]


class Settings(BaseSettings):
    ENVIRONMENT: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )

    # Base de datos
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 3
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_POOL_PING: bool = True

    # Seguridad
    SECRET_KEY: str = ""
    FIELD_ENCRYPTION_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 12 horas
    LOG_LEVEL: str = "INFO"
    INTERNAL_REGISTRATION_TOKEN: str = ""
    INTERNAL_PROVISIONING_TOKEN: str = ""
    INIT_DB_ON_STARTUP: bool = False

    # Facturación y APIs externas
    API_URL: str = "https://facturacion.apisperu.com/api/v1"
    API_TOKEN: str = ""
    SMARTPSE_BASE_URL: str = "https://panel.smartpse.pe"
    SMARTPSE_API_TOKEN: str = ""
    SMARTPSE_TIMEOUT_SECONDS: int = 30
    DNIRUC_API_URL: str = "https://dniruc.apisperu.com/api/v1"
    DNIRUC_TOKEN: str = ""
    GEMINI_API_KEY: str = ""
    EMISSION_MODE_DEFAULT: str = "async"
    EMISSION_WORKER_POLL_SECONDS: int = 2
    EMISSION_MAX_ATTEMPTS: int = 5
    EMISSION_RETRY_BASE_SECONDS: int = 15
    EMISSION_PROCESSING_TIMEOUT_SECONDS: int = 300
    EMISSION_WORKER_CONCURRENCY: int = 1
    FISCAL_ENV: str = Field(
        default="",
        validation_alias=AliasChoices("FISCAL_ENV", "FISCAL_ENVIRONMENT"),
    )

    # Storage / assets
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "printflow-archivos"
    SUPABASE_PUBLIC_ASSETS_BUCKET: str = "inkora-public-assets"

    # App / runtime
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ALLOW_ORIGINS_RAW: str = Field(
        default="",
        validation_alias=AliasChoices("CORS_ALLOW_ORIGINS", "CORS_ALLOW_ORIGINS_RAW"),
    )
    MAX_LOGO_UPLOAD_BYTES: int = 25 * 1024 * 1024
    MAX_AI_UPLOAD_BYTES: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("LOG_LEVEL")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("EMISSION_MODE_DEFAULT")
    @classmethod
    def normalize_emission_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"sync", "async"}:
            raise ValueError("EMISSION_MODE_DEFAULT debe ser 'sync' o 'async'.")
        return normalized

    @field_validator("FISCAL_ENV")
    @classmethod
    def normalize_fiscal_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            return ""
        if normalized not in _VALID_FISCAL_ENVIRONMENTS:
            raise ValueError("FISCAL_ENV debe ser 'beta' o 'production'.")
        return normalized

    def model_post_init(self, __context) -> None:
        if not self.DATABASE_URL.strip():
            raise ValueError("DATABASE_URL es obligatoria.")

        if not self.SECRET_KEY.strip():
            raise ValueError("SECRET_KEY es obligatoria.")

        if not self.INTERNAL_PROVISIONING_TOKEN and self.INTERNAL_REGISTRATION_TOKEN:
            object.__setattr__(
                self,
                "INTERNAL_PROVISIONING_TOKEN",
                self.INTERNAL_REGISTRATION_TOKEN,
            )

        if not self.FISCAL_ENV:
            object.__setattr__(
                self,
                "FISCAL_ENV",
                "production" if self.is_production else "beta",
            )

        if self.is_production and self.INIT_DB_ON_STARTUP:
            raise ValueError("INIT_DB_ON_STARTUP no está permitido en producción.")

        if self.is_production and self.FISCAL_ENV != "production":
            raise ValueError(
                "FISCAL_ENV debe ser 'production' cuando ENVIRONMENT es production."
            )

        if not self.is_production and self.FISCAL_ENV == "production":
            raise ValueError(
                "FISCAL_ENV='production' solo está permitido cuando ENVIRONMENT es production."
            )

        if self.is_non_local and self.BACKEND_URL.startswith(
            ("http://localhost", "http://127.0.0.1")
        ):
            raise ValueError(
                "BACKEND_URL debe apuntar a una URL real en staging/producción."
            )

        if self.is_non_local and not self.has_supabase_storage:
            raise ValueError(
                "SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY son obligatorias en staging/produccion."
            )

    @property
    def APP_ENV(self) -> str:
        return self.ENVIRONMENT

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT in _LOCAL_ENVIRONMENTS

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT in {"production", "prod"}

    @property
    def is_non_local(self) -> bool:
        return self.is_staging or self.is_production

    @property
    def has_supabase_storage(self) -> bool:
        return bool(
            self.SUPABASE_URL.strip()
            and (self.SUPABASE_SERVICE_ROLE_KEY.strip() or self.SUPABASE_KEY.strip())
        )

    @property
    def is_fiscal_beta(self) -> bool:
        return self.FISCAL_ENV == "beta"

    @property
    def is_fiscal_production(self) -> bool:
        return self.FISCAL_ENV == "production"

    @property
    def cors_allow_origins(self) -> list[str]:
        if self.CORS_ALLOW_ORIGINS_RAW.strip():
            return [
                origin.strip()
                for origin in self.CORS_ALLOW_ORIGINS_RAW.split(",")
                if origin.strip()
            ]

        if self.is_non_local:
            return list(_DEFAULT_REMOTE_CORS_ORIGINS)

        return list(_DEFAULT_LOCAL_CORS_ORIGINS)


settings = Settings()

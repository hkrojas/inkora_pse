import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Base de Datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    
    # Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "tu_clave_secreta_super_segura")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Facturación y APIs Externas (APIsPERU)
    # URL de Producción para Facturación
    API_URL: str = os.getenv("API_URL", "https://facturacion.apisperu.com/api/v1") 
    # Token global por defecto (opcional, se prefiere el del usuario)
    API_TOKEN: str = os.getenv("API_TOKEN", "") 
    
    # Consulta DNI/RUC (APIsPERU)
    DNIRUC_API_URL: str = os.getenv("DNIRUC_API_URL", "https://dniruc.apisperu.com/api/v1")
    DNIRUC_TOKEN: str = os.getenv("DNIRUC_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6Imtlbm5lZHlyb2phczAxMDY0QGdtYWlsLmNvbSJ9.3sopEO4OjTDovbXV46k8g48sxbP55W3MEbke16Im-uw")

    # Inteligencia Artificial (Google Gemini)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "ignore" 

settings = Settings()
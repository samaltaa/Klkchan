from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Define aquí todas tus variables de entorno
    DB_URL: str

    class Config:
        env_file = ".env"

# Instancia global para usar en toda la app
settings = Settings()

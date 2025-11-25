from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar


class Settings(BaseSettings):
    # ⚠️ Os valores abaixo são apenas defaults, devem ser definidos no .env
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    # Propriedade computada para a URL da BD
    # Usamos o driver "postgresql+psycopg2"
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
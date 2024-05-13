from pydantic import MongoDsn
from pydantic_settings import BaseSettings


class MongoSettings(BaseSettings):
    MONGO_HOST: str
    MONGO_PORT: int
    MONGO_NAME: str

    @property
    def MONGO_DATABASE_URI(self) -> MongoDsn:
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_NAME}"


class Settings(MongoSettings):
    TOKEN: str

    class Config:
        env_file = "infra-rlt/.env"


settings: Settings = Settings()

TYPES = ("hour", "day", "week", "month")

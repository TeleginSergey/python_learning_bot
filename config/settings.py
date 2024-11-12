from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str = '7066916393:AAFOAZtmf__xt9Fl-XSM9GpTQvddn98skkI'
    # BOT_WEBHOOK_URL: str

    DB_HOST: str = 'localhost'
    DB_PORT: int = 5432
    DB_NAME: str = 'postgres'
    DB_USER: str = 'postgres'
    DB_PASSWORD: str = 'postgres'

    RABBIT_HOST: str = 'localhost'
    RABBIT_PORT: int = 5673
    RABBIT_USER: str = 'guest'
    RABBIT_PASSWORD: str = 'guest'

    REDIS_HOST: str = 'localhost'
    REDIS_PORT: str = '6379'

    USER_TASK_QUEUE_TEMPLATE: str = 'user_tasks.{user_id}'

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def rabbit_url(self) -> str:
        return f"amqp://{self.RABBIT_USER}:{self.RABBIT_PASSWORD}@{self.RABBIT_HOST}:{self.RABBIT_PORT}/"

    class Config:
        env_file = "config/.env"


settings = Settings()

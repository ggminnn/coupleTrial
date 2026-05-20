import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    OPENAI_API_KEY: str = ""

    # 이메일 설정
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

# LangChain/OpenAI 클라이언트가 os.environ에서 키를 읽으므로 명시적으로 설정
if settings.OPENAI_API_KEY:
    os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)

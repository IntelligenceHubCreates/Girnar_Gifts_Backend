from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_server: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str
    cloudinary_api_secret: str
    cloudinary_api_key: str
    cloudinary_cloud_name: str

    class Config:
        env_file = ".env"


settings = Settings()

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
    cloudinary_folder: str = "girnar-gifts"
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # RazorPay Configuration
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str
    razorpay_receipt_prefix: str = "girnar_"

    # CORS
    cors_origins: str = "https://girnargifts.com,https://www.girnargifts.com"

    # Brand (used by emails/invoices)
    brand_name: str = "Girnar Gifts"
    brand_support_email: str = "support@girnargifts.com"
    brand_gstin: str = "GSTIN-HERE"

    class Config:
        env_file = ".env"


settings = Settings()

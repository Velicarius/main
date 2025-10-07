import os
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Загружаем .env.dev если файл существует
if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")

class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    secret_key: str = Field(default="dev-secret", alias="SECRET_KEY")

    # Database settings
    database_url_env: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="ai_portfolio", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    qdrant_host: str = Field(default="qdrant", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # EOD Feature Flags
    eod_enable: bool = Field(default=False, alias="EOD_ENABLE")
    eod_source: str = Field(default="stooq", alias="EOD_SOURCE")
    eod_schedule_cron: str = Field(default="30 23 * * *", alias="EOD_SCHEDULE_CRON")  # 23:30 Europe/Warsaw
    stq_timeout: int = Field(default=10, alias="STQ_TIMEOUT")
    
    # Admin token for EOD endpoints
    admin_token: str | None = Field(default=None, alias="ADMIN_TOKEN")

    # News Aggregation Feature Flags
    news_enable: bool = Field(default=False, alias="NEWS_ENABLE")
    news_timeout: int = Field(default=10, alias="NEWS_TIMEOUT")
    news_cache_ttl: int = Field(default=300, alias="NEWS_CACHE_TTL")  # 5 minutes default

    # News Provider API Keys
    finnhub_api_key: str | None = Field(default=None, alias="FINNHUB_API_KEY")
    alphavantage_api_key: str | None = Field(default=None, alias="ALPHAVANTAGE_API_KEY")
    newsapi_api_key: str | None = Field(default=None, alias="NEWSAPI_API_KEY")

    # Crypto Positions Feature Flags
    feature_crypto_positions: bool = Field(default=False, alias="FEATURE_CRYPTO_POSITIONS")
    crypto_price_ttl_seconds: int = Field(default=60, alias="CRYPTO_PRICE_TTL_SECONDS")
    crypto_price_primary: str = Field(default="binance", alias="CRYPTO_PRICE_PRIMARY")
    crypto_allowed_symbols: str = Field(default="BTC,ETH,SOL,BNB,ADA,XRP,DOGE,AVAX,MATIC", alias="CRYPTO_ALLOWED_SYMBOLS")
    
    # AI Model Defaults
    default_insights_model: str = Field(default="llama3.1:8b", alias="DEFAULT_INSIGHTS_MODEL")
    default_insights_provider: str = Field(default="ollama", alias="DEFAULT_INSIGHTS_PROVIDER")
    default_news_model: str = Field(default="llama3.1:8b", alias="DEFAULT_NEWS_MODEL")
    default_news_provider: str = Field(default="ollama", alias="DEFAULT_NEWS_PROVIDER")
    
    # News Cache Settings
    news_cache_enabled: bool = Field(default=True, alias="NEWS_CACHE_ENABLED")
    news_cache_ttl_seconds: int = Field(default=300, alias="NEWS_CACHE_TTL_SECONDS")  # 5 minutes
    news_cache_max_articles: int = Field(default=100, alias="NEWS_CACHE_MAX_ARTICLES")

    @property
    def database_url(self) -> str:
        """Get database URL from environment or construct from individual components"""
        if self.database_url_env:
            return self.database_url_env
        
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def debug_dump(self) -> None:
        """Print database URL for debugging (without password)"""
        url = self.database_url
        # Hide password in debug output
        if "://" in url and "@" in url:
            parts = url.split("://")
            if len(parts) == 2:
                scheme = parts[0]
                rest = parts[1]
                if "@" in rest:
                    user_pass, host_db = rest.split("@", 1)
                    if ":" in user_pass:
                        user, _ = user_pass.split(":", 1)
                        safe_url = f"{scheme}://{user}:***@{host_db}"
                    else:
                        safe_url = f"{scheme}://{user_pass}:***@{host_db}"
                else:
                    safe_url = url
            else:
                safe_url = url
        else:
            safe_url = url
        
        print(f"Database URL: {safe_url}")
        print(f"Postgres Host: {self.postgres_host}")
        print(f"Postgres Port: {self.postgres_port}")
        print(f"Postgres DB: {self.postgres_db}")
        print(f"Postgres User: {self.postgres_user}")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "dystore"
    mysql_password: str = ""
    mysql_database: str = "dystore"

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"

    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-128k"

    playwright_user_data_dir: Path = Path("/data/playwright")
    scraper_headless: bool = True
    # Merchant scraper browser source:
    #   "playwright" — launch headless Chromium inside the container (fast, but bytedance risk engine flags it)
    #   "cdp"        — connect to a real Chrome running on the host via DevTools Protocol (real fingerprint, real IP)
    merchant_browser_mode: str = "playwright"
    # When mode=cdp: CDP endpoint of host Chrome. Default works for Docker Desktop on Mac/Windows.
    merchant_cdp_url: str = "http://host.docker.internal:9222"
    public_scraper_backend: str = "playwright"
    huitu_api_key: str = ""
    chanmama_api_key: str = ""

    app_host: str = "0.0.0.0"
    app_port: int = 8080
    log_level: str = "INFO"
    tz: str = "Asia/Shanghai"

    @property
    def mysql_dsn(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()

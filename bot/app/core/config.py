import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel

class Settings(BaseModel):
    BOT_TOKEN: str
    TIMEZONE: str = "Europe/Moscow"
    SUPERADMIN_ID: Optional[int] = None
    DEFAULT_TTL_SECONDS: int = 900
    DB_PATH: str = "queue.db"
    LOG_LEVEL: str = "INFO"
    
    # Network settings
    NETWORK_CONNECT_TIMEOUT: float = 10.0
    NETWORK_READ_TIMEOUT: float = 30.0
    NETWORK_TOTAL_TIMEOUT: float = 60.0
    NETWORK_MAX_RETRIES: int = 5
    NETWORK_BASE_DELAY: float = 1.0
    NETWORK_MAX_DELAY: float = 30.0
    NETWORK_BACKOFF_FACTOR: float = 2.0
    NETWORK_MONITOR_INTERVAL: float = 30.0

def _to_int(name: str, default: Optional[int] = None) -> Optional[int]:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except Exception:
        return default

def _to_float(name: str, default: Optional[float] = None) -> Optional[float]:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    try:
        return float(v)
    except Exception:
        return default

def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан в .env")
    
    
    return Settings(
        BOT_TOKEN=token,
        TIMEZONE=os.getenv("TIMEZONE", "Europe/Moscow"),
        SUPERADMIN_ID=_to_int("SUPERADMIN_ID", None),
        DEFAULT_TTL_SECONDS=int(os.getenv("DEFAULT_TTL_SECONDS", "900")),
        DB_PATH=os.getenv("DB_PATH", "queue.db"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        # Network settings
        NETWORK_CONNECT_TIMEOUT=_to_float("NETWORK_CONNECT_TIMEOUT", 10.0),
        NETWORK_READ_TIMEOUT=_to_float("NETWORK_READ_TIMEOUT", 30.0),
        NETWORK_TOTAL_TIMEOUT=_to_float("NETWORK_TOTAL_TIMEOUT", 60.0),
        NETWORK_MAX_RETRIES=_to_int("NETWORK_MAX_RETRIES", 5),
        NETWORK_BASE_DELAY=_to_float("NETWORK_BASE_DELAY", 1.0),
        NETWORK_MAX_DELAY=_to_float("NETWORK_MAX_DELAY", 30.0),
        NETWORK_BACKOFF_FACTOR=_to_float("NETWORK_BACKOFF_FACTOR", 2.0),
        NETWORK_MONITOR_INTERVAL=_to_float("NETWORK_MONITOR_INTERVAL", 30.0),
    )

settings = load_settings()

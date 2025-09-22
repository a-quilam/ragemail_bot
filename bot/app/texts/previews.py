from app.core.timefmt import fmt_expiry
from zoneinfo import ZoneInfo

def build_preview(alias: str, text: str, delete_at: int, tz: ZoneInfo) -> str:
    # This one is for final preview, maybe add more details later
    return f"{text}\n\n<b>{alias}</b>\n{fmt_expiry(delete_at, tz)}"

def build_ttl_preview(alias: str, text: str, delete_at: int, tz: ZoneInfo) -> str:
    # This one is for TTL selection
    return f"{text}\n\n<b>{alias}</b>\n{fmt_expiry(delete_at, tz)}"

from datetime import datetime
from zoneinfo import ZoneInfo

DOW = ["пн","вт","ср","чт","пт","сб","вс"]

def fmt_expiry(ts: int, tz: ZoneInfo) -> str:
    dt = datetime.fromtimestamp(ts, tz)
    now = datetime.now(tz)
    hhmm = dt.strftime("%H:%M")
    if dt.date() == now.date():
        return f"🔥 Сгорит в {hhmm}"
    return f"🔥 Сгорит в {hhmm} {DOW[dt.weekday()]}"

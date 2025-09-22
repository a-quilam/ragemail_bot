import re
from typing import Optional, Tuple

USERNAME_RE = re.compile(r"^@([A-Za-z0-9_]{5,})$")
TME_RE = re.compile(r"^https?://t\.me/(c/)?([A-Za-z0-9_]{5,}|\d+)/?(\d+)?$")

def parse_channel_ref(s: str) -> Tuple[str, str]:
    s = s.strip()
    m = USERNAME_RE.match(s)
    if m:
        return ("username", m.group(1))
    m = TME_RE.match(s)
    if m:
        if m.group(1) == "c/":
            return ("internal", m.group(2))  # numeric internal id without -100 prefix
        else:
            return ("username", m.group(2))
    if s.startswith("-100") and s[4:].isdigit():
        return ("id", s)
    raise ValueError("Некорректная ссылка/ID канала. Укажите @username, ссылку t.me или -100…")

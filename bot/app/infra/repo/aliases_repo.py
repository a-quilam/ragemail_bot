import aiosqlite
from typing import Optional, List

class AliasesRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def get_for_today(self, user_id: int, day_key: str) -> Optional[str]:
        row = await (await self.db.execute("SELECT alias FROM aliases WHERE user_id=? AND valid_day=?", (user_id, day_key))).fetchone()
        return row[0] if row else None

    async def set_for_today(self, user_id: int, alias: str, day_key: str) -> None:
        await self.db.execute(
            "INSERT INTO aliases(user_id, alias, valid_day) VALUES(?,?,?) ON CONFLICT(user_id, valid_day) DO UPDATE SET alias=excluded.alias",
            (user_id, alias, day_key),
        )
        await self.db.commit()

import aiosqlite
from typing import Optional, Tuple, List

class RelaysRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create(self, a_user_id: int, b_user_id: int, a_alias: str, b_alias: str, expires_at: int) -> int:
        cur = await self.db.execute(
            "INSERT INTO relays(a_user_id,b_user_id,a_alias,b_alias,expires_at) VALUES(?,?,?,?,?)",
            (a_user_id, b_user_id, a_alias, b_alias, expires_at),
        )
        await self.db.commit()
        return cur.lastrowid

    async def get_active_for(self, user_id: int, now_ts: int) -> Optional[Tuple[int,int,int,str,str,int]]:
        return await (await self.db.execute(
            "SELECT id,a_user_id,b_user_id,a_alias,b_alias,expires_at FROM relays WHERE (a_user_id=? OR b_user_id=?) AND expires_at> ? ORDER BY id DESC LIMIT 1",
            (user_id, user_id, now_ts),
        )).fetchone()

    async def close_all_for(self, user_id: int, now_ts: int) -> None:
        await self.db.execute(
            "UPDATE relays SET expires_at=? WHERE (a_user_id=? OR b_user_id=?) AND expires_at> ?",
            (now_ts, user_id, user_id, now_ts),
        )
        await self.db.commit()

    async def purge_expired(self, now_ts: int) -> None:
        await self.db.execute("DELETE FROM relays WHERE expires_at<=?", (now_ts,))
        await self.db.commit()

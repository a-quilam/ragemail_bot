import aiosqlite
from typing import Optional, Tuple, List

class RelaysRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create(self, a_user_id: int, b_user_id: int, a_alias: str, b_alias: str, expires_at: int, a_message_id: int = None, b_message_id: int = None) -> int:
        cur = await self.db.execute(
            "INSERT INTO relays(a_user_id,b_user_id,a_alias,b_alias,expires_at,a_message_id,b_message_id) VALUES(?,?,?,?,?,?,?)",
            (a_user_id, b_user_id, a_alias, b_alias, expires_at, a_message_id, b_message_id),
        )
        await self.db.commit()
        return cur.lastrowid

    async def get_active_for(self, user_id: int, now_ts: int) -> Optional[Tuple[int,int,int,str,str,int,int,int]]:
        return await (await self.db.execute(
            "SELECT id,a_user_id,b_user_id,a_alias,b_alias,expires_at,a_message_id,b_message_id FROM relays WHERE (a_user_id=? OR b_user_id=?) AND expires_at> ? ORDER BY id DESC LIMIT 1",
            (user_id, user_id, now_ts),
        )).fetchone()

    async def close_all_for(self, user_id: int, now_ts: int) -> None:
        await self.db.execute(
            "UPDATE relays SET expires_at=? WHERE (a_user_id=? OR b_user_id=?) AND expires_at> ?",
            (now_ts, user_id, user_id, now_ts),
        )
        await self.db.commit()

    async def get_by_message_id(self, user_id: int, message_id: int, now_ts: int) -> Optional[Tuple[int,int,int,str,str,int,int,int]]:
        """Получить активный релей по ID сообщения пользователя"""
        return await (await self.db.execute(
            "SELECT id,a_user_id,b_user_id,a_alias,b_alias,expires_at,a_message_id,b_message_id FROM relays WHERE ((a_user_id=? AND a_message_id=?) OR (b_user_id=? AND b_message_id=?)) AND expires_at> ? ORDER BY id DESC LIMIT 1",
            (user_id, message_id, user_id, message_id, now_ts),
        )).fetchone()

    async def purge_expired(self, now_ts: int) -> None:
        await self.db.execute("DELETE FROM relays WHERE expires_at<=?", (now_ts,))
        await self.db.commit()

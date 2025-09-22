import aiosqlite
from typing import Optional, Tuple, List

class PostsRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def add(self, chat_id: int, message_id: int, author_id: int, alias: str, base_text: str, base_delete_at: int, delete_at: int) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO posts(chat_id,message_id,author_id,alias,base_text,base_delete_at,delete_at) VALUES(?,?,?,?,?,?,?)",
            (chat_id, message_id, author_id, alias, base_text, base_delete_at, delete_at),
        )
        await self.db.commit()

    async def get(self, chat_id: int, message_id: int) -> Optional[Tuple[int,int,int,str,str,int,int]]:
        return await (await self.db.execute(
            "SELECT chat_id,message_id,author_id,alias,base_text,base_delete_at,delete_at FROM posts WHERE chat_id=? AND message_id=?",
            (chat_id, message_id),
        )).fetchone()

    async def set_delete_at(self, chat_id: int, message_id: int, delete_at: int) -> None:
        await self.db.execute("UPDATE posts SET delete_at=? WHERE chat_id=? AND message_id=?", (delete_at, chat_id, message_id))
        await self.db.commit()

    async def list_expired(self, now_ts: int):
        return await (await self.db.execute("SELECT chat_id, message_id FROM posts WHERE delete_at <= ?", (now_ts,))).fetchall()

    async def delete(self, chat_id: int, message_id: int) -> None:
        await self.db.execute("DELETE FROM posts WHERE chat_id=? AND message_id=?", (chat_id, message_id))
        await self.db.commit()

    async def batch_delete(self, posts: List[Tuple[int, int]]) -> None:
        """Batch удаление постов"""
        if not posts:
            return
        
        # Используем транзакцию для batch операции
        await self.db.execute("BEGIN TRANSACTION")
        try:
            for chat_id, message_id in posts:
                await self.db.execute("DELETE FROM posts WHERE chat_id=? AND message_id=?", (chat_id, message_id))
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

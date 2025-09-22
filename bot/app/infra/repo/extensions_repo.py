import aiosqlite
from typing import Dict, List

KIND_TO_SECONDS = {
    "15m": 15*60, 
    "30m": 30*60, 
    "1h": 3600, 
    "2h": 2*3600, 
    "3h": 3*3600, 
    "6h": 6*3600, 
    "12h": 12*3600, 
    "24h": 24*3600
}

class ExtensionsRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def toggle(self, post_key: str, user_id: int, kind: str) -> bool:
        row = await (await self.db.execute(
            "SELECT active FROM extensions WHERE post_key=? AND user_id=? AND kind=?",
            (post_key, user_id, kind),
        )).fetchone()
        if not row:
            await self.db.execute(
                "INSERT INTO extensions(post_key,user_id,kind,active) VALUES(?,?,?,1)",
                (post_key, user_id, kind),
            )
            await self.db.commit()
            return True
        active = 0 if row[0] else 1
        await self.db.execute(
            "UPDATE extensions SET active=? WHERE post_key=? AND user_id=? AND kind=?",
            (active, post_key, user_id, kind),
        )
        await self.db.commit()
        return bool(active)

    async def counts(self, post_key: str) -> Dict[str, int]:
        res = {"15m": 0, "30m": 0, "1h": 0, "2h": 0, "3h": 0, "6h": 0, "12h": 0, "24h": 0}
        async with self.db.execute(
            "SELECT kind, COUNT(*) FROM extensions WHERE post_key=? AND active=1 GROUP BY kind",
            (post_key,),
        ) as cur:
            async for kind, cnt in cur:
                if kind in res:
                    res[kind] = cnt
        return res

    async def total_extension_seconds(self, post_key: str) -> int:
        total = 0
        async with self.db.execute(
            "SELECT kind, COUNT(*) FROM extensions WHERE post_key=? AND active=1 GROUP BY kind",
            (post_key,),
        ) as cur:
            async for kind, cnt in cur:
                total += KIND_TO_SECONDS.get(kind, 0) * int(cnt)
        return total

    async def delete_post(self, post_key: str) -> None:
        await self.db.execute("DELETE FROM extensions WHERE post_key=?", (post_key,))

    async def batch_delete_posts(self, post_keys: List[str]) -> None:
        """Batch удаление расширений для нескольких постов"""
        if not post_keys:
            return
        
        # Используем транзакцию для batch операции
        await self.db.execute("BEGIN TRANSACTION")
        try:
            for post_key in post_keys:
                await self.db.execute("DELETE FROM extensions WHERE post_key=?", (post_key,))
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

import aiosqlite
from typing import List, Optional
from datetime import datetime, timedelta

class AliasBlocksRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def block_user_by_alias_word(self, word: str, admin_id: int, mailbox_id: Optional[int] = None, reason: str = "", duration_hours: int = 24) -> bool:
        """Заблокировать пользователя по слову из псевдонима для конкретного ящика"""
        # Валидация входных параметров
        if not isinstance(word, str) or not word.strip():
            raise ValueError("Word must be a non-empty string")
        
        if not isinstance(admin_id, int) or admin_id <= 0:
            raise ValueError("Admin ID must be a positive integer")
        
        if mailbox_id is not None and (not isinstance(mailbox_id, int) or mailbox_id <= 0):
            raise ValueError("Mailbox ID must be a positive integer or None")
        
        if not isinstance(reason, str):
            reason = str(reason) if reason is not None else ""
        
        if not isinstance(duration_hours, int) or duration_hours <= 0:
            raise ValueError("Duration hours must be a positive integer")
        
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        await self.db.execute(
            "INSERT INTO alias_blocks (blocked_word, admin_id, mailbox_id, reason, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (word.lower(), admin_id, mailbox_id, reason, expires_at.isoformat(), datetime.now().isoformat())
        )
        await self.db.commit()
        return True

    async def unblock_user_by_alias_word(self, word: str, mailbox_id: Optional[int] = None) -> bool:
        """Разблокировать пользователя по слову из псевдонима для конкретного ящика"""
        # Валидация входных параметров
        if not isinstance(word, str) or not word.strip():
            raise ValueError("Word must be a non-empty string")
        
        if mailbox_id is not None and (not isinstance(mailbox_id, int) or mailbox_id <= 0):
            raise ValueError("Mailbox ID must be a positive integer or None")
        
        if mailbox_id is not None:
            # Удаляем блокировку только для конкретного ящика
            await self.db.execute(
                "DELETE FROM alias_blocks WHERE blocked_word = ? AND mailbox_id = ?",
                (word.lower(), mailbox_id)
            )
        else:
            # Удаляем все блокировки этого слова (глобально)
            await self.db.execute(
                "DELETE FROM alias_blocks WHERE blocked_word = ?",
                (word.lower(),)
            )
        await self.db.commit()
        return True

    async def is_word_blocked(self, word: str, mailbox_id: Optional[int] = None) -> bool:
        """Проверить, заблокировано ли слово для конкретного ящика"""
        # Валидация входных параметров
        if not isinstance(word, str) or not word.strip():
            return False
        
        if mailbox_id is not None and (not isinstance(mailbox_id, int) or mailbox_id <= 0):
            return False
        
        # Проверяем активные блокировки
        if mailbox_id is not None:
            # Проверяем блокировки для конкретного ящика И глобальные блокировки
            row = await (await self.db.execute(
                "SELECT 1 FROM alias_blocks WHERE blocked_word = ? AND (expires_at IS NULL OR expires_at > ?) AND (mailbox_id = ? OR mailbox_id IS NULL)",
                (word.lower(), datetime.now().isoformat(), mailbox_id)
            )).fetchone()
        else:
            # Проверяем только глобальные блокировки
            row = await (await self.db.execute(
                "SELECT 1 FROM alias_blocks WHERE blocked_word = ? AND (expires_at IS NULL OR expires_at > ?) AND mailbox_id IS NULL",
                (word.lower(), datetime.now().isoformat())
            )).fetchone()
        return row is not None

    async def get_blocked_words(self, mailbox_id: Optional[int] = None) -> List[dict]:
        """Получить список заблокированных слов для конкретного ящика"""
        # Валидация входных параметров
        if mailbox_id is not None and (not isinstance(mailbox_id, int) or mailbox_id <= 0):
            return []
        
        if mailbox_id is not None:
            # Получаем блокировки для конкретного ящика И глобальные блокировки
            async with self.db.execute(
                "SELECT blocked_word, admin_id, mailbox_id, reason, expires_at, created_at FROM alias_blocks WHERE (expires_at IS NULL OR expires_at > ?) AND (mailbox_id = ? OR mailbox_id IS NULL) ORDER BY created_at DESC",
                (datetime.now().isoformat(), mailbox_id)
            ) as cursor:
                return [
                    {
                        "word": row[0],
                        "admin_id": row[1],
                        "mailbox_id": row[2],
                        "reason": row[3],
                        "expires_at": row[4],
                        "created_at": row[5]
                    }
                    async for row in cursor
                ]
        else:
            # Получаем все блокировки
            async with self.db.execute(
                "SELECT blocked_word, admin_id, mailbox_id, reason, expires_at, created_at FROM alias_blocks WHERE expires_at IS NULL OR expires_at > ? ORDER BY created_at DESC",
                (datetime.now().isoformat(),)
            ) as cursor:
                return [
                    {
                        "word": row[0],
                        "admin_id": row[1],
                        "mailbox_id": row[2],
                        "reason": row[3],
                        "expires_at": row[4],
                        "created_at": row[5]
                    }
                    async for row in cursor
                ]

    async def cleanup_expired_blocks(self) -> int:
        """Очистить истекшие блокировки"""
        result = await self.db.execute(
            "DELETE FROM alias_blocks WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (datetime.now().isoformat(),)
        )
        await self.db.commit()
        return result.rowcount

    async def get_user_blocks(self, user_id: int, mailbox_id: Optional[int] = None) -> List[dict]:
        """Получить блокировки, созданные пользователем для конкретного ящика"""
        # Валидация входных параметров
        if not isinstance(user_id, int) or user_id <= 0:
            return []
        
        if mailbox_id is not None and (not isinstance(mailbox_id, int) or mailbox_id <= 0):
            return []
        
        if mailbox_id is not None:
            async with self.db.execute(
                "SELECT blocked_word, mailbox_id, reason, expires_at, created_at FROM alias_blocks WHERE admin_id = ? AND (mailbox_id = ? OR mailbox_id IS NULL) ORDER BY created_at DESC",
                (user_id, mailbox_id)
            ) as cursor:
                return [
                    {
                        "word": row[0],
                        "mailbox_id": row[1],
                        "reason": row[2],
                        "expires_at": row[3],
                        "created_at": row[4]
                    }
                    async for row in cursor
                ]
        else:
            async with self.db.execute(
                "SELECT blocked_word, mailbox_id, reason, expires_at, created_at FROM alias_blocks WHERE admin_id = ? ORDER BY created_at DESC",
                (user_id,)
            ) as cursor:
                return [
                    {
                        "word": row[0],
                        "mailbox_id": row[1],
                        "reason": row[2],
                        "expires_at": row[3],
                        "created_at": row[4]
                    }
                    async for row in cursor
                ]

import aiosqlite
from typing import Optional, List
from datetime import datetime, timedelta

class UserCooldownsRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def set_cooldown(self, user_id: int, alias: str, mailbox_id: Optional[int] = None, duration_hours: int = 24, reason: str = "") -> bool:
        """Установить кулдаун для пользователя по псевдониму для конкретного ящика"""
        cooldown_until = datetime.now() + timedelta(hours=duration_hours)
        
        await self.db.execute(
            "INSERT OR REPLACE INTO user_cooldowns (user_id, alias, mailbox_id, cooldown_until, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, alias, mailbox_id, cooldown_until.isoformat(), reason, datetime.now().isoformat())
        )
        await self.db.commit()
        return True

    async def is_user_on_cooldown(self, user_id: int, mailbox_id: Optional[int] = None) -> Optional[dict]:
        """Проверить, находится ли пользователь на кулдауне для конкретного ящика"""
        if mailbox_id is not None:
            # Проверяем кулдаун для конкретного ящика И глобальные кулдауны
            row = await (await self.db.execute(
                "SELECT alias, mailbox_id, cooldown_until, reason FROM user_cooldowns WHERE user_id = ? AND (mailbox_id = ? OR mailbox_id IS NULL)",
                (user_id, mailbox_id)
            )).fetchone()
        else:
            # Проверяем только глобальные кулдауны
            row = await (await self.db.execute(
                "SELECT alias, mailbox_id, cooldown_until, reason FROM user_cooldowns WHERE user_id = ? AND mailbox_id IS NULL",
                (user_id,)
            )).fetchone()
        
        if not row:
            return None
        
        alias, row_mailbox_id, cooldown_until_str, reason = row
        cooldown_until = datetime.fromisoformat(cooldown_until_str)
        
        if datetime.now() < cooldown_until:
            return {
                "alias": alias,
                "mailbox_id": row_mailbox_id,
                "cooldown_until": cooldown_until,
                "reason": reason
            }
        else:
            # Кулдаун истек, удаляем запись
            await self.remove_cooldown(user_id, mailbox_id)
            return None

    async def remove_cooldown(self, user_id: int, mailbox_id: Optional[int] = None) -> bool:
        """Удалить кулдаун пользователя для конкретного ящика"""
        if mailbox_id is not None:
            # Удаляем кулдаун только для конкретного ящика
            await self.db.execute(
                "DELETE FROM user_cooldowns WHERE user_id = ? AND mailbox_id = ?",
                (user_id, mailbox_id)
            )
        else:
            # Удаляем все кулдауны пользователя
            await self.db.execute(
                "DELETE FROM user_cooldowns WHERE user_id = ?",
                (user_id,)
            )
        await self.db.commit()
        return True

    async def get_all_cooldowns(self, mailbox_id: Optional[int] = None) -> List[dict]:
        """Получить все активные кулдауны для конкретного ящика"""
        if mailbox_id is not None:
            # Получаем кулдауны для конкретного ящика И глобальные кулдауны
            rows = await (await self.db.execute(
                "SELECT user_id, alias, mailbox_id, cooldown_until, reason FROM user_cooldowns WHERE cooldown_until > ? AND (mailbox_id = ? OR mailbox_id IS NULL)",
                (datetime.now().isoformat(), mailbox_id)
            )).fetchall()
        else:
            # Получаем все кулдауны
            rows = await (await self.db.execute(
                "SELECT user_id, alias, mailbox_id, cooldown_until, reason FROM user_cooldowns WHERE cooldown_until > ?",
                (datetime.now().isoformat(),)
            )).fetchall()
        
        cooldowns = []
        for row in rows:
            user_id, alias, row_mailbox_id, cooldown_until_str, reason = row
            cooldown_until = datetime.fromisoformat(cooldown_until_str)
            cooldowns.append({
                "user_id": user_id,
                "alias": alias,
                "mailbox_id": row_mailbox_id,
                "cooldown_until": cooldown_until,
                "reason": reason
            })
        
        return cooldowns

    async def set_cooldown_by_alias(self, alias: str, mailbox_id: Optional[int] = None, duration_hours: int = 24, reason: str = "") -> bool:
        """Установить кулдаун для всех пользователей с определенным псевдонимом для конкретного ящика"""
        # Находим всех пользователей с этим псевдонимом
        from app.infra.repo.aliases_repo import AliasesRepo
        aliases_repo = AliasesRepo(self.db)
        
        # Получаем пользователей с этим псевдонимом
        async with self.db.execute(
            "SELECT user_id FROM aliases WHERE alias = ?",
            (alias,)
        ) as cursor:
            users = await cursor.fetchall()
        
        cooldown_until = datetime.now() + timedelta(hours=duration_hours)
        
        for (user_id,) in users:
            await self.db.execute(
                "INSERT OR REPLACE INTO user_cooldowns (user_id, alias, mailbox_id, cooldown_until, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, alias, mailbox_id, cooldown_until.isoformat(), reason, datetime.now().isoformat())
            )
        
        await self.db.commit()
        return True

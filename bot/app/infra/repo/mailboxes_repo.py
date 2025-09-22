import aiosqlite
import logging
from typing import Optional, List, Tuple, Dict
from .base_repo import BaseRepo

class MailboxesRepo(BaseRepo):
    def __init__(self, db: aiosqlite.Connection):
        super().__init__(db)

    async def create(self, title: str, channel_id: int, creator_id: int) -> int:
        if not isinstance(title, str) or not title.strip():
            logging.error(f"Invalid title in create: {title}")
            raise ValueError("Title cannot be empty")
        if not isinstance(channel_id, int) or channel_id >= 0:
            logging.error(f"Invalid channel_id in create: {channel_id}")
            raise ValueError("Invalid channel_id")
        if not isinstance(creator_id, int) or creator_id <= 0:
            logging.error(f"Invalid creator_id in create: {creator_id}")
            raise ValueError("Invalid creator_id")
        
        try:
            cur = await self.db.execute("INSERT INTO mailboxes(title, channel_id, creator_id) VALUES(?, ?, ?)", (title, channel_id, creator_id))
            await self.db.commit()
            return cur.lastrowid
        except Exception as e:
            logging.error(f"Error creating mailbox: {e}")
            raise

    async def get(self, mailbox_id: int) -> Optional[Tuple[int, str, int, Optional[int], Optional[str], int]]:
        if not isinstance(mailbox_id, int) or mailbox_id <= 0:
            logging.error(f"Invalid mailbox_id in get: {mailbox_id}")
            return None
        
        try:
            return await (await self.db.execute("SELECT id, title, channel_id, stat_day, stat_time, creator_id FROM mailboxes WHERE id=?", (mailbox_id,))).fetchone()
        except Exception as e:
            logging.error(f"Error getting mailbox {mailbox_id}: {e}")
            return None

    async def set_stats_schedule(self, mailbox_id: int, day: int, time_hhmm: str) -> None:
        if not isinstance(mailbox_id, int) or mailbox_id <= 0:
            logging.error(f"Invalid mailbox_id in set_stats_schedule: {mailbox_id}")
            return
        if not isinstance(day, int) or day < 1 or day > 7:
            logging.error(f"Invalid day in set_stats_schedule: {day}")
            return
        if not isinstance(time_hhmm, str) or not time_hhmm:
            logging.error(f"Invalid time_hhmm in set_stats_schedule: {time_hhmm}")
            return
        
        try:
            await self.db.execute("UPDATE mailboxes SET stat_day=?, stat_time=? WHERE id=?", (day, time_hhmm, mailbox_id))
            await self.db.commit()
        except Exception as e:
            logging.error(f"Error setting stats schedule for mailbox {mailbox_id}: {e}")
            raise

    async def list_all(self) -> List[Tuple[int, str, int, Optional[int], Optional[str], int]]:
        try:
            rows = await (await self.db.execute("SELECT id, title, channel_id, stat_day, stat_time, creator_id FROM mailboxes ORDER BY id" )).fetchall()
            # Проверка целостности данных
            valid_mailboxes = []
            for row in rows:
                if len(row) >= 6 and row[0] is not None and row[1] is not None and row[2] is not None and row[5] is not None:
                    valid_mailboxes.append(row)
                else:
                    logging.warning(f"Invalid mailbox data: {row}")
            return valid_mailboxes
        except Exception as e:
            logging.error(f"Error listing all mailboxes: {e}")
            return []

    async def get_by_creator(self, creator_id: int) -> List[Tuple[int, str, int, Optional[int], Optional[str], int]]:
        """Получить все ящики, созданные пользователем"""
        if not isinstance(creator_id, int) or creator_id <= 0:
            logging.error(f"Invalid creator_id in get_by_creator: {creator_id}")
            return []
        
        try:
            return await (await self.db.execute("SELECT id, title, channel_id, stat_day, stat_time, creator_id FROM mailboxes WHERE creator_id=? ORDER BY id", (creator_id,))).fetchall()
        except Exception as e:
            logging.error(f"Error getting mailboxes by creator {creator_id}: {e}")
            return []

    async def is_creator(self, mailbox_id: int, user_id: int) -> bool:
        """Проверить, является ли пользователь создателем ящика"""
        if not isinstance(mailbox_id, int) or mailbox_id <= 0:
            logging.error(f"Invalid mailbox_id in is_creator: {mailbox_id}")
            return False
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id in is_creator: {user_id}")
            return False
        
        try:
            row = await (await self.db.execute("SELECT creator_id FROM mailboxes WHERE id=?", (mailbox_id,))).fetchone()
            return row and row[0] == user_id
        except Exception as e:
            logging.error(f"Error checking if user {user_id} is creator of mailbox {mailbox_id}: {e}")
            return False

    async def get_by_channel_id(self, channel_id: int) -> Optional[int]:
        """Получить ID ящика по ID канала"""
        if not isinstance(channel_id, int) or channel_id >= 0:
            logging.error(f"Invalid channel_id in get_by_channel_id: {channel_id}")
            return None
        
        try:
            row = await (await self.db.execute("SELECT id FROM mailboxes WHERE channel_id=?", (channel_id,))).fetchone()
            return row[0] if row else None
        except Exception as e:
            logging.error(f"Error getting mailbox by channel_id {channel_id}: {e}")
            return None

    async def batch_get(self, mailbox_ids: List[int]) -> Dict[int, Tuple[int, str, int, Optional[int], Optional[str], int]]:
        """Получить несколько ящиков одним запросом"""
        if not mailbox_ids or not isinstance(mailbox_ids, list):
            return {}
        
        # Валидация всех ID
        valid_ids = []
        for mailbox_id in mailbox_ids:
            if isinstance(mailbox_id, int) and mailbox_id > 0:
                valid_ids.append(mailbox_id)
            else:
                logging.warning(f"Invalid mailbox_id in batch_get: {mailbox_id}")
        
        if not valid_ids:
            return {}
        
        try:
            placeholders = ','.join('?' * len(valid_ids))
            rows = await (await self.db.execute(
                f"SELECT id, title, channel_id, stat_day, stat_time, creator_id FROM mailboxes WHERE id IN ({placeholders})",
                valid_ids
            )).fetchall()
            
            return {row[0]: row for row in rows}
        except Exception as e:
            logging.error(f"Error batch getting mailboxes: {e}")
            return {}

    async def get_mailboxes_paginated(self, page: int, page_size: int) -> Tuple[List[Tuple[int, str, int, Optional[int], Optional[str], int]], int]:
        """
        Получить ящики с пагинацией.
        
        Args:
            page: Номер страницы (начиная с 1)
            page_size: Размер страницы
            
        Returns:
            Кортеж (список ящиков, общее количество)
        """
        if not isinstance(page, int) or page < 1:
            logging.error(f"Invalid page in get_mailboxes_paginated: {page}")
            return [], 0
        if not isinstance(page_size, int) or page_size < 1:
            logging.error(f"Invalid page_size in get_mailboxes_paginated: {page_size}")
            return [], 0
        
        try:
            offset = (page - 1) * page_size
            
            # Получаем ящики для страницы
            mailboxes = await self.execute_query_all(
                "SELECT id, title, channel_id, stat_day, stat_time, creator_id FROM mailboxes ORDER BY id LIMIT ? OFFSET ?",
                (page_size, offset)
            )
            
            # Получаем общее количество
            total = await self.count("SELECT COUNT(*) FROM mailboxes")
            
            return mailboxes, total
        except Exception as e:
            logging.error(f"Error getting mailboxes paginated: {e}")
            return [], 0

    async def get_mailboxes_by_creator_paginated(self, creator_id: int, page: int, page_size: int) -> Tuple[List[Tuple[int, str, int, Optional[int], Optional[str], int]], int]:
        """
        Получить ящики создателя с пагинацией.
        
        Args:
            creator_id: ID создателя
            page: Номер страницы (начиная с 1)
            page_size: Размер страницы
            
        Returns:
            Кортеж (список ящиков, общее количество)
        """
        if not isinstance(creator_id, int) or creator_id <= 0:
            logging.error(f"Invalid creator_id in get_mailboxes_by_creator_paginated: {creator_id}")
            return [], 0
        if not isinstance(page, int) or page < 1:
            logging.error(f"Invalid page in get_mailboxes_by_creator_paginated: {page}")
            return [], 0
        if not isinstance(page_size, int) or page_size < 1:
            logging.error(f"Invalid page_size in get_mailboxes_by_creator_paginated: {page_size}")
            return [], 0
        
        try:
            offset = (page - 1) * page_size
            
            # Получаем ящики создателя для страницы
            mailboxes = await self.execute_query_all(
                "SELECT id, title, channel_id, stat_day, stat_time, creator_id FROM mailboxes WHERE creator_id=? ORDER BY id LIMIT ? OFFSET ?",
                (creator_id, page_size, offset)
            )
            
            # Получаем общее количество ящиков создателя
            total = await self.count("SELECT COUNT(*) FROM mailboxes WHERE creator_id=?", (creator_id,))
            
            return mailboxes, total
        except Exception as e:
            logging.error(f"Error getting mailboxes by creator paginated: {e}")
            return [], 0

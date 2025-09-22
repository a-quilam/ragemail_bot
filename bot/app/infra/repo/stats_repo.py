import aiosqlite
import logging
from typing import List, Tuple

class StatsRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def inc(self, day: str, key: str) -> None:
        if not isinstance(day, str) or not day.strip():
            logging.error(f"Invalid day in inc: {day}")
            return
        if not isinstance(key, str) or not key.strip():
            logging.error(f"Invalid key in inc: {key}")
            return
        
        try:
            await self.db.execute(
                "INSERT INTO stats(day,key,cnt) VALUES(?,?,1) ON CONFLICT(day,key) DO UPDATE SET cnt=cnt+1",
                (day, key),
            )
            await self.db.commit()
        except Exception as e:
            logging.error(f"Error incrementing stats for day={day}, key={key}: {e}")
            raise

    async def last_7_days(self, since_day: str):
        if not isinstance(since_day, str) or not since_day.strip():
            logging.error(f"Invalid since_day in last_7_days: {since_day}")
            return []
        
        try:
            return await (await self.db.execute(
                "SELECT day, key, SUM(cnt) FROM stats WHERE day >= ? GROUP BY day, key ORDER BY day",
                (since_day,),
            )).fetchall()
        except Exception as e:
            logging.error(f"Error getting last 7 days stats since {since_day}: {e}")
            return []

    async def get_stats_for_mailbox(self, mailbox_id: int) -> dict:
        """Получить статистику для конкретного ящика"""
        if not isinstance(mailbox_id, int) or mailbox_id <= 0:
            logging.error(f"Invalid mailbox_id in get_stats_for_mailbox: {mailbox_id}")
            return {}
        
        # Пока возвращаем пустую статистику, так как структура БД не поддерживает привязку к ящикам
        # В будущем можно добавить поле mailbox_id в таблицу stats
        try:
            # Здесь можно добавить логику для получения статистики по ящику
            # Пока возвращаем пустой словарь
            return {}
        except Exception as e:
            logging.error(f"Error getting stats for mailbox {mailbox_id}: {e}")
            return {}

    async def get_aggregated_stats(self, since_day: str, group_by: str = "day") -> dict:
        """Получить агрегированную статистику"""
        if not isinstance(since_day, str) or not since_day.strip():
            logging.error(f"Invalid since_day in get_aggregated_stats: {since_day}")
            return {}
        if not isinstance(group_by, str) or group_by not in ["day", "key"]:
            logging.error(f"Invalid group_by in get_aggregated_stats: {group_by}")
            return {}
        
        try:
            if group_by == "day":
                query = """
                    SELECT day, key, SUM(cnt) as total
                    FROM stats 
                    WHERE day >= ? 
                    GROUP BY day, key 
                    ORDER BY day, key
                """
            elif group_by == "key":
                query = """
                    SELECT key, SUM(cnt) as total
                    FROM stats 
                    WHERE day >= ? 
                    GROUP BY key 
                    ORDER BY total DESC
                """
            else:
                raise ValueError("group_by must be 'day' or 'key'")
            
            rows = await (await self.db.execute(query, (since_day,))).fetchall()
            
            if group_by == "day":
                result = {}
                for day, key, total in rows:
                    if day not in result:
                        result[day] = {}
                    result[day][key] = total
                return result
            else:
                return {key: total for key, total in rows}
        except Exception as e:
            logging.error(f"Error getting aggregated stats: {e}")
            return {}

    async def get_top_keys(self, since_day: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Получить топ ключей по количеству"""
        if not isinstance(since_day, str) or not since_day.strip():
            logging.error(f"Invalid since_day in get_top_keys: {since_day}")
            return []
        if not isinstance(limit, int) or limit < 1:
            logging.error(f"Invalid limit in get_top_keys: {limit}")
            return []
        
        try:
            rows = await (await self.db.execute(
                "SELECT key, SUM(cnt) as total FROM stats WHERE day >= ? GROUP BY key ORDER BY total DESC LIMIT ?",
                (since_day, limit)
            )).fetchall()
            return [(key, total) for key, total in rows]
        except Exception as e:
            logging.error(f"Error getting top keys: {e}")
            return []

    async def get_daily_totals(self, since_day: str) -> List[Tuple[str, int]]:
        """Получить общие суммы по дням"""
        if not isinstance(since_day, str) or not since_day.strip():
            logging.error(f"Invalid since_day in get_daily_totals: {since_day}")
            return []
        
        try:
            rows = await (await self.db.execute(
                "SELECT day, SUM(cnt) as total FROM stats WHERE day >= ? GROUP BY day ORDER BY day",
                (since_day,)
            )).fetchall()
            return [(day, total) for day, total in rows]
        except Exception as e:
            logging.error(f"Error getting daily totals: {e}")
            return []

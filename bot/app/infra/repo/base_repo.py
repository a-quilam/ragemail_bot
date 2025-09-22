"""
Базовый класс для репозиториев
"""
import aiosqlite
from typing import Any, List, Optional, Tuple
from abc import ABC, abstractmethod

class BaseRepo(ABC):
    """Базовый класс для всех репозиториев"""
    
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def execute_query(self, query: str, params: Tuple[Any, ...] = ()) -> Any:
        """Выполнить SELECT запрос и вернуть результат"""
        return await (await self.db.execute(query, params)).fetchone()
    
    async def execute_query_all(self, query: str, params: Tuple[Any, ...] = ()) -> List[Any]:
        """Выполнить SELECT запрос и вернуть все результаты"""
        return await (await self.db.execute(query, params)).fetchall()
    
    async def execute_update(self, query: str, params: Tuple[Any, ...] = ()) -> None:
        """Выполнить INSERT/UPDATE/DELETE запрос"""
        await self.db.execute(query, params)
        await self.db.commit()
    
    async def execute_batch(self, queries: List[Tuple[str, Tuple[Any, ...]]]) -> None:
        """Выполнить несколько запросов в транзакции"""
        await self.db.execute("BEGIN TRANSACTION")
        try:
            for query, params in queries:
                await self.db.execute(query, params)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
    
    async def execute_batch_with_placeholders(self, base_query: str, params_list: List[Tuple[Any, ...]]) -> None:
        """Выполнить один запрос с множественными параметрами"""
        if not params_list:
            return
            
        await self.db.execute("BEGIN TRANSACTION")
        try:
            for params in params_list:
                await self.db.execute(base_query, params)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
    
    async def exists(self, query: str, params: Tuple[Any, ...] = ()) -> bool:
        """Проверить существование записи"""
        row = await self.execute_query(query, params)
        return row is not None
    
    async def count(self, query: str, params: Tuple[Any, ...] = ()) -> int:
        """Подсчитать количество записей"""
        row = await self.execute_query(query, params)
        return row[0] if row else 0

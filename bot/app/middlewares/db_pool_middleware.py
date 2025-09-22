"""
Middleware для использования connection pool
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.infra.db_pool import get_db_pool

class DatabasePoolMiddleware(BaseMiddleware):
    """
    Middleware для предоставления соединений из пула
    для обработчиков сообщений и callback'ов.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события с предоставлением соединения из пула.
        
        Args:
            handler: Обработчик события
            event: Событие Telegram
            data: Данные для обработчика
            
        Returns:
            Результат обработки события
        """
        db_pool = await get_db_pool()
        
        async with db_pool.get_connection() as db_conn:
            # Добавляем соединение в данные для обработчика
            data['db_conn'] = db_conn
            return await handler(event, data)

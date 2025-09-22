"""
Event-driven кэш ролей без TTL - обновляется только при реальных изменениях
"""
import asyncio
import logging
from typing import Dict, Optional, Set, Callable, Any
from app.core.config import settings

class EventDrivenRoleCache:
    """
    Кэш ролей, который обновляется только при реальных событиях изменения ролей
    Без TTL - данные остаются актуальными до явного изменения
    """
    
    def __init__(self):
        self._cache: Dict[int, str] = {}  # user_id -> role
        self._lock = asyncio.Lock()
        self._superadmin_id = settings.SUPERADMIN_ID
        self._stats = {
            'hits': 0,
            'misses': 0,
            'updates': 0,
            'invalidations': 0,
            'events_processed': 0
        }
        self._event_handlers: Set[Callable] = set()
    
    async def get_role(self, user_id: int, fetch_func) -> str:
        """
        Получить роль пользователя с кэшированием
        
        Args:
            user_id: ID пользователя
            fetch_func: Функция для получения роли из БД (async)
            
        Returns:
            Роль пользователя
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return "user"
        
        # Проверяем superadmin
        if self._superadmin_id and user_id == self._superadmin_id:
            return "superadmin"
        
        async with self._lock:
            # Проверяем кэш
            if user_id in self._cache:
                self._stats['hits'] += 1
                return self._cache[user_id]
            
            # Кэш промах - получаем из БД
            self._stats['misses'] += 1
            try:
                role = await fetch_func(user_id)
                if not role:
                    role = "user"
                
                # Сохраняем в кэш
                self._cache[user_id] = role
                self._stats['updates'] += 1
                
                return role
            except Exception as e:
                logging.error(f"Error fetching role for user {user_id}: {e}")
                return "user"
    
    async def update_role(self, user_id: int, new_role: str) -> None:
        """
        Обновить роль пользователя в кэше
        
        Args:
            user_id: ID пользователя
            new_role: Новая роль
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return
        
        async with self._lock:
            old_role = self._cache.get(user_id, "user")
            self._cache[user_id] = new_role
            self._stats['updates'] += 1
            self._stats['events_processed'] += 1
            
            logging.info(f"Role cache updated for user {user_id}: {old_role} -> {new_role}")
            
            # Уведомляем обработчики событий
            await self._notify_event_handlers('role_changed', {
                'user_id': user_id,
                'old_role': old_role,
                'new_role': new_role
            })
    
    async def invalidate_user(self, user_id: int) -> None:
        """
        Инвалидировать кэш для конкретного пользователя
        
        Args:
            user_id: ID пользователя
        """
        async with self._lock:
            if user_id in self._cache:
                old_role = self._cache[user_id]
                del self._cache[user_id]
                self._stats['invalidations'] += 1
                self._stats['events_processed'] += 1
                
                logging.info(f"Role cache invalidated for user {user_id} (was: {old_role})")
                
                # Уведомляем обработчики событий
                await self._notify_event_handlers('role_invalidated', {
                    'user_id': user_id,
                    'old_role': old_role
                })
    
    async def invalidate_all(self) -> None:
        """
        Очистить весь кэш
        """
        async with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._stats['invalidations'] += cleared_count
            self._stats['events_processed'] += 1
            
            logging.info(f"Role cache cleared: {cleared_count} entries removed")
            
            # Уведомляем обработчики событий
            await self._notify_event_handlers('cache_cleared', {
                'cleared_count': cleared_count
            })
    
    async def add_user(self, user_id: int, role: str = "user") -> None:
        """
        Добавить нового пользователя в кэш
        
        Args:
            user_id: ID пользователя
            role: Роль пользователя
        """
        async with self._lock:
            self._cache[user_id] = role
            self._stats['updates'] += 1
            self._stats['events_processed'] += 1
            
            logging.info(f"New user added to role cache: {user_id} -> {role}")
            
            # Уведомляем обработчики событий
            await self._notify_event_handlers('user_added', {
                'user_id': user_id,
                'role': role
            })
    
    async def remove_user(self, user_id: int) -> None:
        """
        Удалить пользователя из кэша
        
        Args:
            user_id: ID пользователя
        """
        await self.invalidate_user(user_id)
    
    def add_event_handler(self, handler: Callable) -> None:
        """
        Добавить обработчик событий
        
        Args:
            handler: Функция-обработчик событий
        """
        self._event_handlers.add(handler)
    
    def remove_event_handler(self, handler: Callable) -> None:
        """
        Удалить обработчик событий
        
        Args:
            handler: Функция-обработчик событий
        """
        self._event_handlers.discard(handler)
    
    async def _notify_event_handlers(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Уведомить все обработчики событий
        
        Args:
            event_type: Тип события
            data: Данные события
        """
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, data)
                else:
                    handler(event_type, data)
            except Exception as e:
                logging.error(f"Error in event handler {handler}: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Получить статистику кэша
        
        Returns:
            Словарь со статистикой
        """
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self._cache),
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'updates': self._stats['updates'],
            'invalidations': self._stats['invalidations'],
            'events_processed': self._stats['events_processed'],
            'event_handlers': len(self._event_handlers)
        }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Получить детальную информацию о кэше
        
        Returns:
            Словарь с информацией о кэше
        """
        return {
            'cache_size': len(self._cache),
            'cached_users': list(self._cache.keys()),
            'stats': self.get_stats()
        }

# Глобальный экземпляр кэша
_event_driven_cache: Optional[EventDrivenRoleCache] = None

def get_event_driven_role_cache() -> EventDrivenRoleCache:
    """
    Получить глобальный экземпляр event-driven кэша ролей
    
    Returns:
        Экземпляр EventDrivenRoleCache
    """
    global _event_driven_cache
    if _event_driven_cache is None:
        _event_driven_cache = EventDrivenRoleCache()
    return _event_driven_cache

def init_event_driven_role_cache() -> EventDrivenRoleCache:
    """
    Инициализировать event-driven кэш ролей
    
    Returns:
        Экземпляр EventDrivenRoleCache
    """
    global _event_driven_cache
    _event_driven_cache = EventDrivenRoleCache()
    return _event_driven_cache

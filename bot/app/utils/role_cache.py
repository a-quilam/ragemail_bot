"""
Кэш для ролей пользователей с автоматическим обновлением
"""
import asyncio
import time
import logging
from typing import Dict, Optional, Set
from app.core.config import settings

class RoleCache:
    """
    Кэш ролей пользователей с TTL и автоматической инвалидацией
    """
    
    def __init__(self, ttl_seconds: int = 300):  # 5 минут по умолчанию
        self._cache: Dict[int, tuple[str, float]] = {}  # user_id -> (role, timestamp)
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
        self._superadmin_id = settings.SUPERADMIN_ID
        self._stats = {
            'hits': 0,
            'misses': 0,
            'updates': 0,
            'invalidations': 0
        }
    
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
        
        current_time = time.time()
        
        async with self._lock:
            # Проверяем кэш
            if user_id in self._cache:
                role, timestamp = self._cache[user_id]
                
                # Проверяем TTL
                if current_time - timestamp < self._ttl:
                    self._stats['hits'] += 1
                    return role
                else:
                    # Кэш устарел, удаляем
                    del self._cache[user_id]
                    self._stats['invalidations'] += 1
            
            # Кэш промах - получаем из БД
            self._stats['misses'] += 1
            try:
                role = await fetch_func(user_id)
                if not role:
                    role = "user"
                
                # Сохраняем в кэш
                self._cache[user_id] = (role, current_time)
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
            current_time = time.time()
            self._cache[user_id] = (new_role, current_time)
            self._stats['updates'] += 1
            logging.info(f"Role cache updated for user {user_id}: {new_role}")
    
    async def invalidate_user(self, user_id: int) -> None:
        """
        Инвалидировать кэш для конкретного пользователя
        
        Args:
            user_id: ID пользователя
        """
        async with self._lock:
            if user_id in self._cache:
                del self._cache[user_id]
                self._stats['invalidations'] += 1
                logging.info(f"Role cache invalidated for user {user_id}")
    
    async def invalidate_all(self) -> None:
        """
        Очистить весь кэш
        """
        async with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._stats['invalidations'] += cleared_count
            logging.info(f"Role cache cleared: {cleared_count} entries removed")
    
    async def cleanup_expired(self) -> int:
        """
        Очистить устаревшие записи из кэша
        
        Returns:
            Количество удаленных записей
        """
        current_time = time.time()
        expired_users = []
        
        async with self._lock:
            for user_id, (role, timestamp) in self._cache.items():
                if current_time - timestamp >= self._ttl:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self._cache[user_id]
                self._stats['invalidations'] += 1
        
        if expired_users:
            logging.info(f"Cleaned up {len(expired_users)} expired role cache entries")
        
        return len(expired_users)
    
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
            'ttl_seconds': self._ttl
        }
    
    async def start_cleanup_task(self, interval_seconds: int = 60) -> None:
        """
        Запустить фоновую задачу очистки кэша
        
        Args:
            interval_seconds: Интервал очистки в секундах
        """
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_expired()
                    await asyncio.sleep(interval_seconds)
                except Exception as e:
                    logging.error(f"Error in role cache cleanup: {e}")
                    await asyncio.sleep(interval_seconds)
        
        asyncio.create_task(cleanup_loop())
        logging.info(f"Role cache cleanup task started (interval: {interval_seconds}s)")

# Глобальный экземпляр кэша
_role_cache: Optional[RoleCache] = None

def get_role_cache() -> RoleCache:
    """
    Получить глобальный экземпляр кэша ролей
    
    Returns:
        Экземпляр RoleCache
    """
    global _role_cache
    if _role_cache is None:
        _role_cache = RoleCache()
    return _role_cache

def init_role_cache(ttl_seconds: int = 300) -> RoleCache:
    """
    Инициализировать кэш ролей с настройками
    
    Args:
        ttl_seconds: Время жизни кэша в секундах
        
    Returns:
        Экземпляр RoleCache
    """
    global _role_cache
    _role_cache = RoleCache(ttl_seconds)
    return _role_cache

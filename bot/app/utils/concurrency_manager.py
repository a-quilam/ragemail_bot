"""
Concurrency management utilities for thread-safe operations
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Set, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import threading
from collections import defaultdict


@dataclass
class LockInfo:
    """Information about a lock"""
    name: str
    acquired_at: float
    acquired_by: str
    timeout: float
    is_shared: bool = False


class ConcurrencyManager:
    """Manages concurrency and prevents race conditions"""
    
    def __init__(self):
        # Словари для хранения блокировок
        self._locks: Dict[str, asyncio.Lock] = {}
        self._shared_locks: Dict[str, asyncio.RLock] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # Информация о блокировках
        self._lock_info: Dict[str, LockInfo] = {}
        
        # Статистика
        self._lock_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'acquired': 0,
            'timeout': 0,
            'deadlock': 0
        })
        
        # Таймауты по умолчанию
        self._default_timeout = 30.0
        self._max_locks = 1000
        
        # Блокировка для управления самими блокировками
        self._manager_lock = asyncio.Lock()
    
    async def acquire_lock(
        self, 
        name: str, 
        timeout: Optional[float] = None,
        shared: bool = False
    ) -> bool:
        """
        Приобрести блокировку
        
        Args:
            name: Имя блокировки
            timeout: Таймаут в секундах
            shared: Использовать shared lock (RLock)
            
        Returns:
            True если блокировка получена, False если таймаут
        """
        if timeout is None:
            timeout = self._default_timeout
        
        async with self._manager_lock:
            # Проверяем лимит блокировок
            if len(self._locks) + len(self._shared_locks) >= self._max_locks:
                logging.warning(f"Maximum number of locks reached: {self._max_locks}")
                return False
            
            # Получаем или создаем блокировку
            if shared:
                if name not in self._shared_locks:
                    self._shared_locks[name] = asyncio.RLock()
                lock = self._shared_locks[name]
            else:
                if name not in self._locks:
                    self._locks[name] = asyncio.Lock()
                lock = self._locks[name]
        
        try:
            # Пытаемся получить блокировку с таймаутом
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            
            # Записываем информацию о блокировке
            self._lock_info[name] = LockInfo(
                name=name,
                acquired_at=time.time(),
                acquired_by=f"thread_{threading.get_ident()}",
                timeout=timeout,
                is_shared=shared
            )
            
            # Обновляем статистику
            self._lock_stats[name]['acquired'] += 1
            
            logging.debug(f"Lock acquired: {name} (shared: {shared})")
            return True
            
        except asyncio.TimeoutError:
            # Таймаут при получении блокировки
            self._lock_stats[name]['timeout'] += 1
            logging.warning(f"Lock timeout: {name} (timeout: {timeout}s)")
            return False
        except Exception as e:
            logging.error(f"Error acquiring lock {name}: {e}")
            return False
    
    async def release_lock(self, name: str) -> bool:
        """
        Освободить блокировку
        
        Args:
            name: Имя блокировки
            
        Returns:
            True если блокировка освобождена, False если ошибка
        """
        try:
            # Проверяем, есть ли блокировка
            if name in self._locks:
                self._locks[name].release()
                if name in self._lock_info:
                    del self._lock_info[name]
                logging.debug(f"Lock released: {name}")
                return True
            elif name in self._shared_locks:
                self._shared_locks[name].release()
                if name in self._lock_info:
                    del self._lock_info[name]
                logging.debug(f"Shared lock released: {name}")
                return True
            else:
                logging.warning(f"Lock not found: {name}")
                return False
                
        except Exception as e:
            logging.error(f"Error releasing lock {name}: {e}")
            return False
    
    async def acquire_semaphore(
        self, 
        name: str, 
        count: int = 1,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Приобрести семафор
        
        Args:
            name: Имя семафора
            count: Количество разрешений
            timeout: Таймаут в секундах
            
        Returns:
            True если семафор получен, False если таймаут
        """
        if timeout is None:
            timeout = self._default_timeout
        
        async with self._manager_lock:
            if name not in self._semaphores:
                self._semaphores[name] = asyncio.Semaphore(count)
        
        try:
            await asyncio.wait_for(
                self._semaphores[name].acquire(), 
                timeout=timeout
            )
            logging.debug(f"Semaphore acquired: {name}")
            return True
        except asyncio.TimeoutError:
            logging.warning(f"Semaphore timeout: {name}")
            return False
        except Exception as e:
            logging.error(f"Error acquiring semaphore {name}: {e}")
            return False
    
    async def release_semaphore(self, name: str) -> bool:
        """
        Освободить семафор
        
        Args:
            name: Имя семафора
            
        Returns:
            True если семафор освобожден, False если ошибка
        """
        try:
            if name in self._semaphores:
                self._semaphores[name].release()
                logging.debug(f"Semaphore released: {name}")
                return True
            else:
                logging.warning(f"Semaphore not found: {name}")
                return False
        except Exception as e:
            logging.error(f"Error releasing semaphore {name}: {e}")
            return False
    
    @asynccontextmanager
    async def lock(self, name: str, timeout: Optional[float] = None, shared: bool = False):
        """
        Контекстный менеджер для блокировок
        
        Args:
            name: Имя блокировки
            timeout: Таймаут в секундах
            shared: Использовать shared lock
        """
        acquired = await self.acquire_lock(name, timeout, shared)
        if not acquired:
            raise asyncio.TimeoutError(f"Failed to acquire lock: {name}")
        
        try:
            yield
        finally:
            await self.release_lock(name)
    
    @asynccontextmanager
    async def semaphore(self, name: str, count: int = 1, timeout: Optional[float] = None):
        """
        Контекстный менеджер для семафоров
        
        Args:
            name: Имя семафора
            count: Количество разрешений
            timeout: Таймаут в секундах
        """
        acquired = await self.acquire_semaphore(name, count, timeout)
        if not acquired:
            raise asyncio.TimeoutError(f"Failed to acquire semaphore: {name}")
        
        try:
            yield
        finally:
            await self.release_semaphore(name)
    
    def get_lock_stats(self) -> Dict[str, Any]:
        """Получить статистику блокировок"""
        current_time = time.time()
        
        # Информация о текущих блокировках
        active_locks = {}
        for name, info in self._lock_info.items():
            active_locks[name] = {
                'acquired_at': info.acquired_at,
                'acquired_by': info.acquired_by,
                'duration': current_time - info.acquired_at,
                'timeout': info.timeout,
                'is_shared': info.is_shared
            }
        
        return {
            'total_locks': len(self._locks),
            'total_shared_locks': len(self._shared_locks),
            'total_semaphores': len(self._semaphores),
            'active_locks': len(active_locks),
            'active_lock_details': active_locks,
            'lock_statistics': dict(self._lock_stats),
            'max_locks': self._max_locks,
            'default_timeout': self._default_timeout
        }
    
    async def cleanup_stale_locks(self, max_age: float = 300.0):
        """
        Очистка устаревших блокировок
        
        Args:
            max_age: Максимальный возраст блокировки в секундах
        """
        current_time = time.time()
        stale_locks = []
        
        for name, info in self._lock_info.items():
            if current_time - info.acquired_at > max_age:
                stale_locks.append(name)
        
        for name in stale_locks:
            logging.warning(f"Cleaning up stale lock: {name}")
            await self.release_lock(name)
            self._lock_stats[name]['deadlock'] += 1
    
    async def shutdown(self):
        """Завершение работы менеджера конкурентности"""
        # Освобождаем все блокировки
        for name in list(self._lock_info.keys()):
            await self.release_lock(name)
        
        # Очищаем словари
        self._locks.clear()
        self._shared_locks.clear()
        self._semaphores.clear()
        self._lock_info.clear()
        
        logging.info("ConcurrencyManager shutdown completed")


# Глобальный экземпляр менеджера конкурентности
_concurrency_manager = ConcurrencyManager()


def get_concurrency_manager() -> ConcurrencyManager:
    """Получить глобальный экземпляр менеджера конкурентности"""
    return _concurrency_manager


# Удобные функции для быстрого доступа
async def acquire_lock(name: str, timeout: Optional[float] = None, shared: bool = False) -> bool:
    """Приобрести блокировку"""
    return await _concurrency_manager.acquire_lock(name, timeout, shared)


async def release_lock(name: str) -> bool:
    """Освободить блокировку"""
    return await _concurrency_manager.release_lock(name)


@asynccontextmanager
async def lock(name: str, timeout: Optional[float] = None, shared: bool = False):
    """Контекстный менеджер для блокировки"""
    async with _concurrency_manager.lock(name, timeout, shared):
        yield


@asynccontextmanager
async def semaphore(name: str, count: int = 1, timeout: Optional[float] = None):
    """Контекстный менеджер для семафора"""
    async with _concurrency_manager.semaphore(name, count, timeout):
        yield


def get_concurrency_stats() -> Dict[str, Any]:
    """Получить статистику конкурентности"""
    return _concurrency_manager.get_lock_stats()

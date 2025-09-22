"""
Connection pool для базы данных
"""
import asyncio
import aiosqlite
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

class DatabasePool:
    """
    Простой connection pool для SQLite базы данных.
    
    Управляет пулом соединений для оптимизации производительности
    и предотвращения блокировок при одновременном доступе.
    """
    
    def __init__(self, db_path: str, pool_size: int = 5):
        """
        Инициализация пула соединений.
        
        Args:
            db_path: Путь к файлу базы данных
            pool_size: Размер пула соединений
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._created_connections = 0
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Инициализация пула соединений"""
        logger.info(f"Initializing database pool with {self.pool_size} connections")
        
        # Создаем начальные соединения
        for _ in range(min(2, self.pool_size)):  # Создаем только 2 соединения изначально
            conn = await self._create_connection()
            await self._pool.put(conn)
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """Создать новое соединение с базой данных"""
        async with self._lock:
            if self._created_connections >= self.pool_size:
                raise RuntimeError("Pool size exceeded")
            
            conn = await aiosqlite.connect(
                self.db_path,
                timeout=30.0,  # Увеличиваем timeout
                isolation_level=None  # Автокоммит для лучшей производительности
            )
            
            # Настраиваем соединение
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA foreign_keys=ON")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=10000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            
            self._created_connections += 1
            logger.debug(f"Created connection {self._created_connections}/{self.pool_size}")
            
            return conn
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[aiosqlite.Connection]:
        """
        Получить соединение из пула.
        
        Yields:
            Соединение с базой данных
            
        Raises:
            RuntimeError: Если не удалось получить соединение
        """
        conn = None
        try:
            # Пытаемся получить соединение из пула
            try:
                conn = await asyncio.wait_for(self._pool.get(), timeout=5.0)
            except asyncio.TimeoutError:
                # Если пул пуст, создаем новое соединение
                if self._created_connections < self.pool_size:
                    conn = await self._create_connection()
                else:
                    # Ждем освобождения соединения
                    conn = await self._pool.get()
            
            yield conn
            
        except Exception as e:
            logger.error(f"Error in database connection: {e}")
            # Закрываем соединение при ошибке
            if conn:
                try:
                    await conn.close()
                except Exception:
                    pass
                self._created_connections -= 1
            raise
        finally:
            # Возвращаем соединение в пул
            if conn:
                try:
                    await self._pool.put(conn)
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
                    # Закрываем соединение если не удалось вернуть в пул
                    try:
                        await conn.close()
                    except Exception:
                        pass
                    self._created_connections -= 1
    
    async def close_all(self) -> None:
        """Закрыть все соединения в пуле"""
        logger.info("Closing all database connections")
        
        while not self._pool.empty():
            try:
                conn = await asyncio.wait_for(self._pool.get(), timeout=1.0)
                await conn.close()
                self._created_connections -= 1
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        
        logger.info(f"Closed {self._created_connections} connections")
    
    async def get_pool_status(self) -> dict:
        """Получить статус пула соединений"""
        return {
            "pool_size": self.pool_size,
            "created_connections": self._created_connections,
            "available_connections": self._pool.qsize(),
            "busy_connections": self._created_connections - self._pool.qsize()
        }

# Глобальный экземпляр пула
_db_pool: Optional[DatabasePool] = None

async def get_db_pool() -> DatabasePool:
    """Получить глобальный экземпляр пула соединений"""
    global _db_pool
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized")
    return _db_pool

async def initialize_db_pool(db_path: str, pool_size: int = 5) -> DatabasePool:
    """Инициализировать глобальный пул соединений"""
    global _db_pool
    if _db_pool is not None:
        await _db_pool.close_all()
    
    _db_pool = DatabasePool(db_path, pool_size)
    await _db_pool.initialize()
    return _db_pool

async def close_db_pool() -> None:
    """Закрыть глобальный пул соединений"""
    global _db_pool
    if _db_pool is not None:
        await _db_pool.close_all()
        _db_pool = None

import aiosqlite
import time
import logging
from typing import Optional, List, Tuple
from .base_repo import BaseRepo
# Safe imports with fallback support
try:
    from app.utils.concurrency_manager import get_concurrency_manager, lock
except ImportError:
    from app.utils import get_concurrency_manager, lock

try:
    from app.utils.transaction_manager import DatabaseTransaction, execute_in_transaction
except ImportError:
    from app.utils import DatabaseTransaction, execute_in_transaction

try:
    from app.utils.backup_manager import get_backup_manager
except ImportError:
    from app.utils import get_backup_manager

try:
    from app.utils.rollback_manager import get_rollback_manager, create_user_role_rollback, create_username_rollback
except ImportError:
    from app.utils import get_rollback_manager, create_user_role_rollback, create_username_rollback

class UsersRepo(BaseRepo):
    def __init__(self, db: aiosqlite.Connection):
        super().__init__(db)
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 минут
        self._is_healthy = True
        self._concurrency_manager = get_concurrency_manager()
        self._transaction_manager = DatabaseTransaction(db)
        self._backup_manager = get_backup_manager()
        self._rollback_manager = get_rollback_manager()

    async def get_role(self, user_id: int) -> str:
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id in get_role: {user_id}")
            return "user"
        
        try:
            row = await self.execute_query("SELECT role FROM users WHERE user_id=?", (user_id,))
            return row[0] if row else "user"
        except Exception as e:
            logging.error(f"Error getting role for user {user_id}: {e}")
            return "user"

    async def get(self, user_id: int) -> Optional[Tuple[int, str, Optional[int], Optional[int], Optional[str]]]:
        """Получить пользователя по ID"""
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id in get: {user_id}")
            return None
        
        try:
            return await self.execute_query(
                "SELECT user_id, role, active_mailbox_id, last_bind_mailbox_id, username FROM users WHERE user_id=?", 
                (user_id,)
            )
        except Exception as e:
            logging.error(f"Error getting user {user_id}: {e}")
            return None

    async def upsert(self, user_id: int, role: Optional[str] = None, username: Optional[str] = None) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id in upsert: {user_id}")
            return
        
        if role is None:
            role = "user"
        
        # Используем блокировку для предотвращения race conditions
        async with lock(f"user_upsert_{user_id}", timeout=10.0):
            # Механизм восстановления после ошибок
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.execute_update(
                        "INSERT INTO users(user_id, role, username) VALUES(?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET role=excluded.role, username=excluded.username",
                        (user_id, role, username)
                    )
                    
                    # Обновляем event-driven кэш ролей
                    try:
                        from app.utils.event_driven_role_cache import get_event_driven_role_cache
                        role_cache = get_event_driven_role_cache()
                        await role_cache.update_role(user_id, role)
                    except Exception as e:
                        logging.warning(f"Failed to update role cache for user {user_id}: {e}")
                    
                    return  # Успешное выполнение
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"Attempt {attempt + 1} failed for upsert user {user_id}: {e}")
                        import asyncio
                        await asyncio.sleep(0.1 * (attempt + 1))
                else:
                    logging.error(f"All attempts failed for upsert user {user_id}: {e}")
                    raise

    async def set_role(self, user_id: int, role: str) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id in set_role: {user_id}")
            return
        if not isinstance(role, str):
            logging.error(f"Invalid role in set_role: {role}")
            return
        
        # Используем транзакцию для атомарного обновления роли
        async with self._transaction_manager.transaction_context(timeout=10.0) as tx_id:
            try:
                # Получаем старую роль для отката
                old_role = await self.execute_query("SELECT role FROM users WHERE user_id=?", (user_id,))
                old_role = old_role[0] if old_role else "user"
                
                # Добавляем операцию в транзакцию
                await self._transaction_manager.add_operation(
                    "UPDATE",
                    "UPDATE users SET role=? WHERE user_id=?",
                    (role, user_id),
                    "UPDATE users SET role=? WHERE user_id=?",  # rollback query
                    (old_role, user_id)  # rollback params
                )
                
                # Создаем операцию отката перед изменением
                rollback_id = await create_user_role_rollback(
                    user_id, 
                    old_role, 
                    role, 
                    ttl=3600  # 1 час на откат
                )
                
                try:
                    # Выполняем обновление
                    await self.execute_update("UPDATE users SET role=? WHERE user_id=?", (role, user_id))
                    
                    # Обновляем event-driven кэш ролей
                    try:
                        from app.utils.event_driven_role_cache import get_event_driven_role_cache
                        role_cache = get_event_driven_role_cache()
                        await role_cache.update_role(user_id, role)
                    except Exception as e:
                        logging.warning(f"Failed to update role cache for user {user_id}: {e}")
                    
                    # Создаем резервную копию после критических изменений роли
                    try:
                        if hasattr(self.db, 'path') and self.db.path:
                            await self._backup_manager.create_database_backup(
                                self.db.path, 
                                f"role_change_{user_id}_{role}_{int(time.time())}"
                            )
                    except Exception as backup_error:
                        logging.warning(f"Failed to create backup after role change: {backup_error}")
                    
                    logging.info(f"Role change rollback operation created: {rollback_id} for user {user_id}")
                    
                except Exception as update_error:
                    # Если обновление не удалось, удаляем операцию отката
                    await self._rollback_manager.delete_rollback_operation(rollback_id)
                    raise update_error
                
            except Exception as e:
                logging.error(f"Error setting role for user {user_id}: {e}")
                raise

    async def set_active_mailbox(self, user_id: int, mailbox_id: int) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id in set_active_mailbox: {user_id}")
            return
        if not isinstance(mailbox_id, int) or mailbox_id <= 0:
            logging.error(f"Invalid mailbox_id in set_active_mailbox: {mailbox_id}")
            return
        
        try:
            await self.execute_update(
                "INSERT INTO users(user_id, active_mailbox_id) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET active_mailbox_id=excluded.active_mailbox_id",
                (user_id, mailbox_id)
            )
        except Exception as e:
            logging.error(f"Error setting active mailbox for user {user_id}: {e}")
            raise

    async def get_active_mailbox(self, user_id: int) -> Optional[int]:
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id in get_active_mailbox: {user_id}")
            return None
        
        try:
            row = await self.execute_query("SELECT active_mailbox_id FROM users WHERE user_id=?", (user_id,))
            return row[0] if row and row[0] is not None else None
        except Exception as e:
            logging.error(f"Error getting active mailbox for user {user_id}: {e}")
            return None

    async def get_all_admins(self) -> List[Tuple[int, str]]:
        """Получить всех администраторов"""
        try:
            rows = await self.execute_query_all("SELECT user_id, role FROM users WHERE role IN ('admin', 'superadmin')")
            # Проверка целостности данных
            valid_admins = []
            for row in rows:
                if len(row) >= 2 and row[0] is not None and row[1] is not None:
                    valid_admins.append((row[0], row[1]))
                else:
                    logging.warning(f"Invalid admin data: {row}")
            return valid_admins
        except Exception as e:
            logging.error(f"Error getting all admins: {e}")
            return []

    async def get_admins(self) -> List[Tuple[int, str]]:
        """Получить всех администраторов (алиас для get_all_admins для совместимости)"""
        return await self.get_all_admins()

    async def get_users_with_active_mailboxes(self) -> List[int]:
        """Получить всех пользователей с активными ящиками"""
        try:
            rows = await self.execute_query_all("SELECT user_id FROM users WHERE active_mailbox_id IS NOT NULL")
            return [row[0] for row in rows]
        except Exception as e:
            logging.error(f"Error getting users with active mailboxes: {e}")
            return []
    
    async def get_by_username(self, username: str) -> Optional[int]:
        """Получить user_id по username"""
        if not username or not isinstance(username, str):
            return None
        
        # Используем семафор для ограничения одновременных запросов
        async with self._concurrency_manager.semaphore(f"username_lookup_{username}", count=5, timeout=5.0):
            # Механизм повторных попыток
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    row = await self.execute_query("SELECT user_id FROM users WHERE username=?", (username,))
                    return row[0] if row else None
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"Attempt {attempt + 1} failed for get_by_username {username}: {e}")
                        import asyncio
                        await asyncio.sleep(0.1 * (attempt + 1))  # Экспоненциальная задержка
                else:
                    logging.error(f"All attempts failed for get_by_username {username}: {e}")
                    return None
    
    async def update_username(self, user_id: int, username: Optional[str]) -> None:
        """Обновить username пользователя"""
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error(f"Invalid user_id for update_username: {user_id}")
            return
        
        # Используем транзакцию для атомарного обновления
        async with self._transaction_manager.transaction_context(timeout=10.0) as tx_id:
            try:
                # Получаем старое значение для отката
                old_username = await self.execute_query("SELECT username FROM users WHERE user_id=?", (user_id,))
                old_username = old_username[0] if old_username else None
                
                # Добавляем операцию в транзакцию
                await self._transaction_manager.add_operation(
                    "UPDATE",
                    "UPDATE users SET username=? WHERE user_id=?",
                    (username, user_id),
                    "UPDATE users SET username=? WHERE user_id=?",  # rollback query
                    (old_username, user_id)  # rollback params
                )
                
                # Создаем операцию отката перед изменением
                rollback_id = await create_username_rollback(
                    user_id, 
                    old_username, 
                    username, 
                    ttl=1800  # 30 минут на откат
                )
                
                try:
                    # Выполняем обновление
                    await self.execute_update("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
                    
                    logging.info(f"Username update rollback operation created: {rollback_id} for user {user_id}")
                    
                except Exception as update_error:
                    # Если обновление не удалось, удаляем операцию отката
                    await self._rollback_manager.delete_rollback_operation(rollback_id)
                    raise update_error
                
            except Exception as e:
                logging.error(f"Error updating username for user {user_id}: {e}")
                raise

    async def get_users_paginated(self, page: int, page_size: int) -> Tuple[List[Tuple[int, str, Optional[int], Optional[int], Optional[str]]], int]:
        """
        Получить пользователей с пагинацией.
        
        Args:
            page: Номер страницы (начиная с 1)
            page_size: Размер страницы
            
        Returns:
            Кортеж (список пользователей, общее количество)
        """
        if not isinstance(page, int) or page < 1:
            logging.error(f"Invalid page in get_users_paginated: {page}")
            return [], 0
        if not isinstance(page_size, int) or page_size < 1:
            logging.error(f"Invalid page_size in get_users_paginated: {page_size}")
            return [], 0
        
        try:
            offset = (page - 1) * page_size
            
            # Получаем пользователей для страницы
            users = await self.execute_query_all(
                "SELECT user_id, role, active_mailbox_id, last_bind_mailbox_id, username FROM users ORDER BY user_id LIMIT ? OFFSET ?",
                (page_size, offset)
            )
            
            # Получаем общее количество
            total = await self.count("SELECT COUNT(*) FROM users")
            
            return users, total
        except Exception as e:
            logging.error(f"Error getting users paginated: {e}")
            return [], 0

    async def get_admins_paginated(self, page: int, page_size: int) -> Tuple[List[Tuple[int, str]], int]:
        """
        Получить администраторов с пагинацией.
        
        Args:
            page: Номер страницы (начиная с 1)
            page_size: Размер страницы
            
        Returns:
            Кортеж (список администраторов, общее количество)
        """
        if not isinstance(page, int) or page < 1:
            logging.error(f"Invalid page in get_admins_paginated: {page}")
            return [], 0
        if not isinstance(page_size, int) or page_size < 1:
            logging.error(f"Invalid page_size in get_admins_paginated: {page_size}")
            return [], 0
        
        try:
            offset = (page - 1) * page_size
            
            # Получаем администраторов для страницы
            admins = await self.execute_query_all(
                "SELECT user_id, role FROM users WHERE role IN ('admin', 'superadmin') ORDER BY user_id LIMIT ? OFFSET ?",
                (page_size, offset)
            )
            
            # Получаем общее количество администраторов
            total = await self.count("SELECT COUNT(*) FROM users WHERE role IN ('admin', 'superadmin')")
            
            return admins, total
        except Exception as e:
            logging.error(f"Error getting admins paginated: {e}")
            return [], 0
    
    async def health_check(self) -> dict:
        """Проверяет состояние репозитория пользователей"""
        current_time = time.time()
        
        # Проверяем, нужно ли обновлять статус
        if current_time - self._last_health_check < self._health_check_interval:
            return {
                "status": "healthy" if self._is_healthy else "unhealthy",
                "last_check": self._last_health_check,
                "cached": True
            }
        
        start_time = time.time()
        
        try:
            # Выполняем базовые операции для проверки
            test_user_id = 999999999  # Тестовый ID
            
            # Проверяем get_role
            role = await self.get_role(test_user_id)
            
            # Проверяем get_all_admins
            admins = await self.get_all_admins()
            
            duration = (time.time() - start_time) * 1000
            
            self._is_healthy = True
            self._last_health_check = current_time
            
            return {
                "status": "healthy",
                "response_time_ms": duration,
                "admins_count": len(admins) if admins else 0,
                "last_check": current_time,
                "cached": False
            }
            
        except Exception as e:
            self._is_healthy = False
            self._last_health_check = current_time
            
            logging.error(f"Health check failed for UsersRepo: {e}")
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": current_time,
                "cached": False
            }
    
    async def is_healthy(self) -> bool:
        """Быстрая проверка состояния репозитория"""
        health_status = await self.health_check()
        return health_status["status"] == "healthy"
    
    async def get_health_metrics(self) -> dict:
        """Получает метрики состояния репозитория"""
        try:
            # Получаем базовые метрики
            total_users = await self.count("SELECT COUNT(*) FROM users")
            total_admins = await self.count("SELECT COUNT(*) FROM users WHERE role IN ('admin', 'superadmin')")
            total_users_with_mailboxes = await self.count("SELECT COUNT(*) FROM users WHERE active_mailbox_id IS NOT NULL")
            
            return {
                "total_users": total_users,
                "total_admins": total_admins,
                "users_with_mailboxes": total_users_with_mailboxes,
                "is_healthy": await self.is_healthy(),
                "last_health_check": self._last_health_check
            }
            
        except Exception as e:
            logging.error(f"Error getting health metrics for UsersRepo: {e}")
            return {
                "error": str(e),
                "is_healthy": False,
                "last_health_check": self._last_health_check
            }

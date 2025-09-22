from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
import time
import logging
from app.infra.repo.users_repo import UsersRepo
# Safe import with fallback support
try:
    from app.utils.circuit_breaker import get_breaker
except ImportError:
    from app.utils import get_breaker

class MailboxContextMiddleware(BaseMiddleware):
    def __init__(self, users: UsersRepo):
        super().__init__()
        self.users = users
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 минут
        self._is_healthy = True
        self._request_count = 0
        self._error_count = 0

    async def __call__(self, handler: Callable[[Dict[str, Any], Any], Awaitable[Any]], event: Any, data: Dict[str, Any]) -> Any:
        import time
        import logging
        from app.utils.performance_logger import performance_logger
        
        start_time = time.time()
        self.increment_request_count()
        
        try:
            # Валидация входных параметров
            if not callable(handler):
                logging.error("Invalid handler type in MailboxContextMiddleware")
                return
            if not isinstance(data, dict):
                logging.error("Invalid data type in MailboxContextMiddleware")
                return
        except Exception as e:
            logging.error(f"Error in MailboxContextMiddleware validation: {e}")
            return
        
        start_time = time.time()
        
        try:
            user = data.get("event_from_user")
            mailbox_id = None
            
            # Проверки на None и валидация пользователя
            if user is None:
                logging.debug("No user in event data")
                data["active_mailbox_id"] = None
                return await handler(event, data)
            
            # Валидация пользователя
            if not hasattr(user, 'id'):
                logging.warning("User object has no 'id' attribute")
                data["active_mailbox_id"] = None
                return await handler(event, data)
            
            if user.id is not None:
                try:
                    # Добавляем circuit breaker для операций с БД
                    db_breaker = get_breaker("database_operations")
                    if db_breaker.is_open():
                        logging.warning("Database circuit breaker is open, skipping active mailbox lookup")
                        mailbox_id = None
                    else:
                        # Добавляем таймаут для операции с БД
                        import asyncio
                        mailbox_id = await asyncio.wait_for(
                            performance_logger.measure_db_operation(
                                "get_active_mailbox",
                                self.users.get_active_mailbox,
                                user.id
                            ),
                            timeout=5.0
                        )
                except Exception as e:
                    logging.error(f"Error getting active mailbox for user {user.id}: {e}")
                    # Обработка сетевых ошибок
                    if "timeout" in str(e).lower():
                        logging.warning(f"Timeout getting active mailbox for user {user.id}")
                    elif "network" in str(e).lower() or "connection" in str(e).lower():
                        logging.warning(f"Network error getting active mailbox for user {user.id}")
                    mailbox_id = None
            else:
                logging.warning(f"User has no valid ID: {user}")
            
            data["active_mailbox_id"] = mailbox_id
            
            # Логируем для отладки
            user_id = None
            if user and hasattr(user, 'id') and user.id is not None:
                try:
                    user_id = int(user.id)
                except (ValueError, TypeError):
                    user_id = None
                    logging.warning(f"Invalid user.id in MailboxContextMiddleware: {user.id}")
            
            if user_id:
                logging.debug(f"MailboxContextMiddleware: user_id={user_id}, active_mailbox_id={mailbox_id}")
            else:
                logging.warning("MailboxContextMiddleware: user_id is None")
            
            return await handler(event, data)
        except Exception as e:
            self.increment_error_count()
            logging.error(f"Error in MailboxContextMiddleware handler: {e}")
            # Продолжаем выполнение, чтобы не блокировать обработку
            return await handler(event, data)
        finally:
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > 50:  # Логируем медленные middleware операции
                performance_logger.log_slow_operation("MailboxContextMiddleware", 50.0)
    
    async def health_check(self) -> dict:
        """Проверяет состояние middleware"""
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
            # Проверяем состояние UsersRepo с circuit breaker
            db_breaker = get_breaker("database_operations")
            if db_breaker.is_open():
                logging.warning("Database circuit breaker is open during health check")
                self._is_healthy = False
                return {
                    "status": "unhealthy",
                    "reason": "database_circuit_breaker_open",
                    "last_check": current_time,
                    "cached": False
                }
            
            users_health = await self.users.health_check()
            
            duration = (time.time() - start_time) * 1000
            
            # Определяем общий статус
            if users_health.get("status") == "healthy":
                self._is_healthy = True
            else:
                self._is_healthy = False
            
            self._last_health_check = current_time
            
            return {
                "status": "healthy" if self._is_healthy else "unhealthy",
                "response_time_ms": duration,
                "users_repo_status": users_health.get("status", "unknown"),
                "request_count": self._request_count,
                "error_count": self._error_count,
                "error_rate": (self._error_count / max(self._request_count, 1)) * 100,
                "last_check": current_time,
                "cached": False
            }
            
        except Exception as e:
            self._is_healthy = False
            self._last_health_check = current_time
            
            logging.error(f"Health check failed for MailboxContextMiddleware: {e}")
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": current_time,
                "cached": False
            }
    
    async def is_healthy(self) -> bool:
        """Быстрая проверка состояния middleware"""
        health_status = await self.health_check()
        return health_status["status"] == "healthy"
    
    async def get_health_metrics(self) -> dict:
        """Получает метрики состояния middleware"""
        try:
            # Проверяем circuit breaker перед получением метрик
            db_breaker = get_breaker("database_operations")
            if db_breaker.is_open():
                return {
                    "middleware_status": "unhealthy",
                    "reason": "database_circuit_breaker_open",
                    "request_count": self._request_count,
                    "error_count": self._error_count,
                    "error_rate": (self._error_count / max(self._request_count, 1)) * 100,
                    "last_health_check": self._last_health_check
                }
            
            users_metrics = await self.users.get_health_metrics()
            
            return {
                "middleware_status": "healthy" if self._is_healthy else "unhealthy",
                "request_count": self._request_count,
                "error_count": self._error_count,
                "error_rate": (self._error_count / max(self._request_count, 1)) * 100,
                "last_health_check": self._last_health_check,
                "users_repo_metrics": users_metrics
            }
            
        except Exception as e:
            logging.error(f"Error getting health metrics for MailboxContextMiddleware: {e}")
            return {
                "error": str(e),
                "middleware_status": "unhealthy",
                "last_health_check": self._last_health_check
            }
    
    def increment_request_count(self):
        """Увеличивает счетчик запросов"""
        self._request_count += 1
    
    def increment_error_count(self):
        """Увеличивает счетчик ошибок"""
        self._error_count += 1

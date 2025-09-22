"""
Сервис мониторинга сетевого соединения
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError

logger = logging.getLogger(__name__)

@dataclass
class ConnectionStats:
    """Статистика соединения"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    network_errors: int = 0
    api_errors: int = 0
    last_success_time: Optional[float] = None
    last_error_time: Optional[float] = None
    consecutive_failures: int = 0
    connection_uptime: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Процент успешных запросов"""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def is_healthy(self) -> bool:
        """Проверяет, здорово ли соединение"""
        return (
            self.success_rate >= 80.0 and  # Минимум 80% успешных запросов
            self.consecutive_failures < 5 and  # Не более 5 последовательных ошибок
            (self.last_success_time is None or 
             time.time() - self.last_success_time < 300)  # Последний успех не более 5 минут назад
        )

class NetworkMonitor:
    """Монитор сетевого соединения"""
    
    def __init__(self, bot: Bot, check_interval: float = 30.0):
        self.bot = bot
        self.check_interval = check_interval
        self.stats = ConnectionStats()
        self.start_time = time.time()
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_callbacks: list[Callable[[bool], None]] = []
        
        logger.info(f"NetworkMonitor initialized with check interval: {check_interval}s")
    
    def add_health_callback(self, callback: Callable[[bool], None]) -> None:
        """Добавляет callback для уведомлений об изменении состояния здоровья соединения"""
        self.health_callbacks.append(callback)
    
    def remove_health_callback(self, callback: Callable[[bool], None]) -> None:
        """Удаляет callback"""
        if callback in self.health_callbacks:
            self.health_callbacks.remove(callback)
    
    async def start_monitoring(self) -> None:
        """Запускает мониторинг соединения"""
        if self.is_monitoring:
            logger.warning("Network monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Network monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Останавливает мониторинг соединения"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Network monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Основной цикл мониторинга"""
        while self.is_monitoring:
            try:
                await self._check_connection_health()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in network monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_connection_health(self) -> None:
        """Проверяет здоровье соединения"""
        try:
            start_time = time.time()
            await self.bot.get_me()
            response_time = time.time() - start_time
            
            # Обновляем статистику
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.last_success_time = time.time()
            self.stats.consecutive_failures = 0
            self.stats.connection_uptime = time.time() - self.start_time
            
            logger.debug(f"Connection health check successful. Response time: {response_time:.3f}s")
            
            # Проверяем, изменилось ли состояние здоровья
            if not self.stats.is_healthy:
                logger.info("Connection health restored")
                await self._notify_health_change(True)
            
        except (TelegramNetworkError, TelegramAPIError) as e:
            # Обновляем статистику ошибок
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.last_error_time = time.time()
            
            if isinstance(e, TelegramNetworkError):
                self.stats.network_errors += 1
                logger.warning(f"Network error during health check: {e}")
            else:
                self.stats.api_errors += 1
                logger.warning(f"API error during health check: {e}")
            
            # Проверяем, изменилось ли состояние здоровья
            if self.stats.is_healthy:
                logger.warning("Connection health degraded")
                await self._notify_health_change(False)
                
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.last_error_time = time.time()
    
    async def _notify_health_change(self, is_healthy: bool) -> None:
        """Уведомляет о изменении состояния здоровья соединения"""
        for callback in self.health_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(is_healthy)
                else:
                    callback(is_healthy)
            except Exception as e:
                logger.error(f"Error in health callback: {e}")
    
    def record_request_success(self) -> None:
        """Записывает успешный запрос"""
        self.stats.total_requests += 1
        self.stats.successful_requests += 1
        self.stats.last_success_time = time.time()
        self.stats.consecutive_failures = 0
    
    def record_request_error(self, error: Exception) -> None:
        """Записывает ошибку запроса"""
        self.stats.total_requests += 1
        self.stats.failed_requests += 1
        self.stats.consecutive_failures += 1
        self.stats.last_error_time = time.time()
        
        if isinstance(error, TelegramNetworkError):
            self.stats.network_errors += 1
        elif isinstance(error, TelegramAPIError):
            self.stats.api_errors += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику соединения"""
        return {
            'total_requests': self.stats.total_requests,
            'successful_requests': self.stats.successful_requests,
            'failed_requests': self.stats.failed_requests,
            'network_errors': self.stats.network_errors,
            'api_errors': self.stats.api_errors,
            'success_rate': self.stats.success_rate,
            'consecutive_failures': self.stats.consecutive_failures,
            'is_healthy': self.stats.is_healthy,
            'connection_uptime': self.stats.connection_uptime,
            'last_success_time': self.stats.last_success_time,
            'last_error_time': self.stats.last_error_time,
        }
    
    def get_health_status(self) -> str:
        """Возвращает текстовое описание состояния здоровья соединения"""
        if self.stats.is_healthy:
            return f"✅ Здоровое соединение (успешность: {self.stats.success_rate:.1f}%)"
        else:
            return (f"⚠️ Проблемы с соединением "
                   f"(успешность: {self.stats.success_rate:.1f}%, "
                   f"последовательных ошибок: {self.stats.consecutive_failures})")

class NetworkMiddleware:
    """Middleware для отслеживания сетевых запросов"""
    
    def __init__(self, monitor: NetworkMonitor):
        self.monitor = monitor
    
    async def __call__(self, handler, event, data):
        """Обрабатывает событие с отслеживанием сетевых запросов"""
        try:
            result = await handler(event, data)
            self.monitor.record_request_success()
            return result
        except (TelegramNetworkError, TelegramAPIError) as e:
            self.monitor.record_request_error(e)
            raise
        except Exception as e:
            # Для других ошибок не записываем как сетевые
            raise

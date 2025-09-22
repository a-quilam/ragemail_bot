"""
Утилиты для логирования производительности
"""
import time
import logging
import gc
import weakref
from functools import wraps
from typing import Callable, Any, Dict, List, Optional
import asyncio
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class PerformanceLogger:
    """Класс для логирования производительности операций"""
    
    def __init__(self):
        # Статистика операций
        self._operation_stats: Dict[str, List[float]] = defaultdict(list)
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._slow_operations: Dict[str, int] = defaultdict(int)
        
        # Управление памятью
        self._memory_cleanup_threshold = 100  # операций
        self._operation_count = 0
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 минут
        
        # Слабые ссылки для отслеживания объектов
        self._tracked_objects: List[weakref.ref] = []
        self._max_tracked_objects = 1000
    
    def _cleanup_memory_if_needed(self):
        """Периодическая очистка памяти"""
        current_time = time.time()
        self._operation_count += 1
        
        # Проверяем, нужно ли очистить память
        should_cleanup = (
            self._operation_count >= self._memory_cleanup_threshold or
            current_time - self._last_cleanup > self._cleanup_interval
        )
        
        if should_cleanup:
            try:
                # Очистка слабых ссылок на удаленные объекты
                self._tracked_objects = [ref for ref in self._tracked_objects if ref() is not None]
                
                # Ограничиваем количество отслеживаемых объектов
                if len(self._tracked_objects) > self._max_tracked_objects:
                    self._tracked_objects = self._tracked_objects[-self._max_tracked_objects:]
                
                # Очистка старых статистик
                for operation in list(self._operation_stats.keys()):
                    if len(self._operation_stats[operation]) > 1000:
                        self._operation_stats[operation] = self._operation_stats[operation][-500:]
                
                # Принудительная сборка мусора
                collected = gc.collect()
                
                self._operation_count = 0
                self._last_cleanup = current_time
                
                if collected > 0:
                    logger.debug(f"Memory cleanup: collected {collected} objects, "
                               f"tracked objects: {len(self._tracked_objects)}")
                
            except Exception as e:
                logger.error(f"Error during memory cleanup: {e}")
    
    def track_object(self, obj: Any) -> weakref.ref:
        """Отслеживание объекта для управления памятью"""
        if len(self._tracked_objects) < self._max_tracked_objects:
            ref = weakref.ref(obj)
            self._tracked_objects.append(ref)
            return ref
        return None
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Получение статистики использования памяти"""
        try:
            # Подсчет активных объектов
            active_objects = sum(1 for ref in self._tracked_objects if ref() is not None)
            
            # Статистика операций
            total_operations = sum(self._operation_counts.values())
            total_slow_operations = sum(self._slow_operations.values())
            
            return {
                "tracked_objects": len(self._tracked_objects),
                "active_objects": active_objects,
                "total_operations": total_operations,
                "total_slow_operations": total_slow_operations,
                "slow_operation_rate": (total_slow_operations / max(total_operations, 1)) * 100,
                "operation_count": self._operation_count,
                "last_cleanup": self._last_cleanup,
                "cleanup_interval": self._cleanup_interval
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}
    
    def log_slow_operation(self, operation_name: str, threshold_ms: float = 100.0):
        """
        Декоратор для логирования медленных операций
        
        Args:
            operation_name: Название операции для логов
            threshold_ms: Порог в миллисекундах, после которого операция считается медленной
        """
        # Валидация входных параметров
        if operation_name is None:
            logger.error("operation_name is None in log_slow_operation")
            return lambda func: func
        if not isinstance(operation_name, str):
            logger.error("Invalid operation_name type in log_slow_operation")
            return lambda func: func
        if threshold_ms is None:
            logger.error("threshold_ms is None in log_slow_operation")
            return lambda func: func
        if not isinstance(threshold_ms, (int, float)) or threshold_ms < 0:
            logger.error("Invalid threshold_ms in log_slow_operation")
            return lambda func: func
            
        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs) -> Any:
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    finally:
                        duration_ms = (time.time() - start_time) * 1000
                        
                        # Обновляем статистику
                        self._operation_counts[operation_name] += 1
                        self._operation_stats[operation_name].append(duration_ms)
                        
                        if duration_ms > threshold_ms:
                            self._slow_operations[operation_name] += 1
                            logger.warning(
                                f"SLOW OPERATION: {operation_name} took {duration_ms:.1f}ms "
                                f"(threshold: {threshold_ms}ms)"
                            )
                        else:
                            logger.debug(f"Operation {operation_name} took {duration_ms:.1f}ms")
                        
                        # Периодическая очистка памяти
                        self._cleanup_memory_if_needed()
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs) -> Any:
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        duration_ms = (time.time() - start_time) * 1000
                        
                        # Обновляем статистику
                        self._operation_counts[operation_name] += 1
                        self._operation_stats[operation_name].append(duration_ms)
                        
                        if duration_ms > threshold_ms:
                            self._slow_operations[operation_name] += 1
                            logger.warning(
                                f"SLOW OPERATION: {operation_name} took {duration_ms:.1f}ms "
                                f"(threshold: {threshold_ms}ms)"
                            )
                        else:
                            logger.debug(f"Operation {operation_name} took {duration_ms:.1f}ms")
                        
                        # Периодическая очистка памяти
                        self._cleanup_memory_if_needed()
                return sync_wrapper
        return decorator

    @staticmethod
    async def measure_db_operation(operation_name: str, operation_func: Callable, *args, **kwargs):
        """
        Измеряет время выполнения операции с базой данных
        
        Args:
            operation_name: Название операции
            operation_func: Функция для выполнения
            *args, **kwargs: Аргументы для функции
            
        Returns:
            Результат выполнения операции
        """
        try:
            # Валидация входных параметров
            if not isinstance(operation_name, str):
                logger.error("Invalid operation_name type in measure_db_operation")
                return None
        except Exception as e:
            logger.error(f"Error in measure_db_operation validation: {e}")
            return None
        
        start_time = time.time()
        try:
            if operation_func is None:
                raise ValueError("operation_func cannot be None")
            if not callable(operation_func):
                raise ValueError("operation_func must be callable")
                
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"DB OPERATION FAILED: {operation_name} failed after {duration_ms:.1f}ms: {e}")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > 50:  # БД операции должны быть быстрыми
                logger.warning(f"SLOW DB OPERATION: {operation_name} took {duration_ms:.1f}ms")
            else:
                logger.debug(f"DB operation {operation_name} took {duration_ms:.1f}ms")

    @staticmethod
    def log_message_processing(message_id: int, user_id: int, handler_name: str, duration_ms: float):
        """
        Логирует время обработки сообщения
        
        Args:
            message_id: ID сообщения
            user_id: ID пользователя
            handler_name: Название обработчика
            duration_ms: Время обработки в миллисекундах
        """
        # Валидация входных параметров
        if not isinstance(message_id, int) or message_id <= 0:
            logger.error("Invalid message_id in log_message_processing")
            return
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error("Invalid user_id in log_message_processing")
            return
        if not isinstance(handler_name, str):
            logger.error("Invalid handler_name type in log_message_processing")
            return
        if not isinstance(duration_ms, (int, float)) or duration_ms < 0:
            logger.error("Invalid duration_ms in log_message_processing")
            return
        
        if duration_ms > 500:  # Медленная обработка
            logger.warning(
                f"SLOW MESSAGE PROCESSING: "
                f"message_id={message_id}, user_id={user_id}, "
                f"handler={handler_name}, duration={duration_ms:.1f}ms"
            )
        elif duration_ms > 200:  # Умеренно медленная
            logger.info(
                f"MODERATE MESSAGE PROCESSING: "
                f"message_id={message_id}, user_id={user_id}, "
                f"handler={handler_name}, duration={duration_ms:.1f}ms"
            )
        else:
            logger.debug(
                f"Message processing: "
                f"message_id={message_id}, user_id={user_id}, "
                f"handler={handler_name}, duration={duration_ms:.1f}ms"
            )

# Глобальный экземпляр для удобства использования
performance_logger = PerformanceLogger()

# Дополнительные утилиты для управления памятью
def get_performance_stats() -> Dict[str, Any]:
    """Получить статистику производительности"""
    return performance_logger.get_memory_stats()

def cleanup_performance_memory():
    """Принудительная очистка памяти"""
    performance_logger._cleanup_memory_if_needed()

def track_performance_object(obj: Any) -> Optional[weakref.ref]:
    """Отслеживание объекта для управления памятью"""
    return performance_logger.track_object(obj)

"""
Circuit Breaker для защиты от сбоев внешних сервисов
"""
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
import asyncio


class CircuitState(Enum):
    """Состояния circuit breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Блокировка запросов
    HALF_OPEN = "half_open"  # Тестирование восстановления


class CircuitBreaker:
    """Circuit Breaker для защиты от сбоев внешних сервисов"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
        name: str = "CircuitBreaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        
        self._lock = asyncio.Lock()
    
    def is_open(self) -> bool:
        """Проверяет, открыт ли circuit breaker"""
        return self.state == CircuitState.OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Выполняет функцию через circuit breaker"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logging.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                else:
                    raise Exception(f"Circuit breaker {self.name} is OPEN")
            
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
                
            except self.expected_exception as e:
                await self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Проверяет, можно ли попытаться сбросить circuit breaker"""
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    async def _on_success(self):
        """Обрабатывает успешное выполнение"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logging.info(f"Circuit breaker {self.name} reset to CLOSED")
        
        self.failure_count = 0
    
    async def _on_failure(self):
        """Обрабатывает неудачное выполнение"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logging.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")
    
    def get_state(self) -> dict:
        """Возвращает текущее состояние circuit breaker"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }
    
    def reset(self):
        """Принудительно сбрасывает circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        logging.info(f"Circuit breaker {self.name} manually reset")


class CircuitBreakerManager:
    """Менеджер для управления несколькими circuit breakers"""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ) -> CircuitBreaker:
        """Получает или создает circuit breaker"""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                name=name
            )
        return self._breakers[name]
    
    def get_all_states(self) -> dict:
        """Возвращает состояние всех circuit breakers"""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}
    
    def reset_all(self):
        """Сбрасывает все circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()
    
    def reset_breaker(self, name: str):
        """Сбрасывает конкретный circuit breaker"""
        if name in self._breakers:
            self._breakers[name].reset()


# Глобальный менеджер circuit breakers
_breaker_manager = CircuitBreakerManager()


def get_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Получает circuit breaker по имени"""
    return _breaker_manager.get_breaker(name, **kwargs)


def get_all_breaker_states() -> dict:
    """Получает состояние всех circuit breakers"""
    return _breaker_manager.get_all_states()


def reset_all_breakers():
    """Сбрасывает все circuit breakers"""
    _breaker_manager.reset_all()


def reset_breaker(name: str):
    """Сбрасывает конкретный circuit breaker"""
    _breaker_manager.reset_breaker(name)

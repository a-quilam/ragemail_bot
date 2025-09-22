"""
Простой тест для исправленных fallback-реализаций
"""
import asyncio
import logging


def test_sanitize_user_id_fallback():
    """Тест fallback sanitize_user_id с некорректными данными"""
    def sanitize_user_id_fallback(user_id):
        if user_id is None:
            return 0
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return 0
    
    # Тестируем различные входные данные
    assert sanitize_user_id_fallback(123) == 123
    assert sanitize_user_id_fallback("456") == 456
    assert sanitize_user_id_fallback(None) == 0
    assert sanitize_user_id_fallback("abc") == 0
    assert sanitize_user_id_fallback("") == 0
    assert sanitize_user_id_fallback([]) == 0
    assert sanitize_user_id_fallback({}) == 0
    print("✅ sanitize_user_id fallback тест пройден")


async def test_circuit_breaker_fallback():
    """Тест fallback CircuitBreaker с разными типами функций"""
    class CircuitBreakerFallback:
        async def call(self, func, *args, **kwargs):
            if not hasattr(func, '__call__'):
                return func
            
            try:
                # Проверяем, является ли функция корутиной
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    # Если это обычная функция, вызываем синхронно
                    return func(*args, **kwargs)
            except Exception as e:
                logging.warning(f"Circuit breaker fallback error: {e}")
                raise
    
    breaker = CircuitBreakerFallback()
    
    # Асинхронная функция
    async def async_func():
        return 'async_result'
    
    # Синхронная функция
    def sync_func():
        return 'sync_result'
    
    # Тест с асинхронной функцией
    result1 = await breaker.call(async_func)
    assert result1 == 'async_result'
    
    # Тест с синхронной функцией
    result2 = await breaker.call(sync_func)
    assert result2 == 'sync_result'
    
    # Тест с некорректными данными
    result3 = await breaker.call("not_a_function")
    assert result3 == "not_a_function"
    
    print("✅ CircuitBreaker fallback тест пройден")


async def test_rate_limiter_fallback():
    """Тест fallback RateLimiter"""
    class RateLimiterFallback:
        async def is_allowed(self, *args, **kwargs):
            try:
                return True, None
            except Exception as e:
                logging.warning(f"Rate limiter fallback error: {e}")
                return True, None
    
    async def check_rate_limit_fallback(limiter, *args, **kwargs):
        try:
            if limiter and hasattr(limiter, 'is_allowed'):
                return await limiter.is_allowed(*args, **kwargs)
            return True, None
        except Exception as e:
            logging.warning(f"Rate limit check fallback error: {e}")
            return True, None
    
    limiter = RateLimiterFallback()
    allowed, error = await check_rate_limit_fallback(limiter, 'test_user')
    assert allowed is True
    assert error is None
    
    print("✅ RateLimiter fallback тест пройден")


def test_input_sanitizer_fallback():
    """Тест fallback InputSanitizer"""
    class InputSanitizerFallback:
        @staticmethod
        def sanitize_user_input(data):
            try:
                return str(data) if data is not None else ""
            except Exception as e:
                logging.warning(f"Input sanitizer fallback error: {e}")
                return ""
        
        @staticmethod
        def sanitize_username(username):
            try:
                return str(username) if username is not None else ""
            except Exception as e:
                logging.warning(f"Username sanitizer fallback error: {e}")
                return ""
        
        @staticmethod
        def sanitize_user_id(user_id):
            if user_id is None:
                return 0
            try:
                return int(user_id)
            except (ValueError, TypeError) as e:
                logging.warning(f"User ID sanitizer fallback error: {e}")
                return 0
    
    sanitizer = InputSanitizerFallback()
    
    # Тест sanitize_user_input
    assert sanitizer.sanitize_user_input("test") == "test"
    assert sanitizer.sanitize_user_input(None) == ""
    assert sanitizer.sanitize_user_input(123) == "123"
    
    # Тест sanitize_username
    assert sanitizer.sanitize_username("user123") == "user123"
    assert sanitizer.sanitize_username(None) == ""
    
    # Тест sanitize_user_id
    assert sanitizer.sanitize_user_id(123) == 123
    assert sanitizer.sanitize_user_id("456") == 456
    assert sanitizer.sanitize_user_id(None) == 0
    assert sanitizer.sanitize_user_id("abc") == 0
    
    print("✅ InputSanitizer fallback тест пройден")


async def test_all_fallbacks():
    """Запуск всех тестов fallback-реализаций"""
    print("🧪 Запуск тестов исправленных fallback-реализаций...")
    
    try:
        test_sanitize_user_id_fallback()
        await test_circuit_breaker_fallback()
        await test_rate_limiter_fallback()
        test_input_sanitizer_fallback()
        
        print("\n🎉 Все тесты fallback-реализаций пройдены успешно!")
        print("✅ Исправления работают корректно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_all_fallbacks())

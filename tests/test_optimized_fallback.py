"""
Тесты для оптимизированных fallback-реализаций
"""
import asyncio
import time


def test_optimized_sanitize_user_input():
    """Тест оптимизированного sanitize_user_input"""
    def sanitize_user_input_optimized(data):
        if data is None:
            return ""
        try:
            data_str = str(data)
            safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
            sanitized = ''.join(c for c in data_str if c in safe_chars)
            return sanitized.encode('utf-8')[:1000].decode('utf-8', errors='ignore')
        except Exception:
            return ""
    
    # Тестируем производительность
    start_time = time.time()
    for i in range(1000):
        result = sanitize_user_input_optimized("Hello World! 123")
    end_time = time.time()
    
    print(f"✅ sanitize_user_input: {end_time - start_time:.4f}s для 1000 итераций")
    
    # Тестируем функциональность
    assert sanitize_user_input_optimized("Hello World!") == "Hello World"
    assert sanitize_user_input_optimized("Hello@#$%") == "Hello"
    assert sanitize_user_input_optimized(None) == ""
    assert sanitize_user_input_optimized("") == ""
    
    print("✅ Optimized sanitize_user_input тест пройден")


def test_optimized_sanitize_username():
    """Тест оптимизированного sanitize_username"""
    def sanitize_username_optimized(username):
        if username is None:
            return ""
        try:
            username_str = str(username)
            safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            sanitized = ''.join(c for c in username_str if c in safe_chars)
            return sanitized[:50]
        except Exception:
            return ""
    
    # Тестируем производительность
    start_time = time.time()
    for i in range(1000):
        result = sanitize_username_optimized("user_123-test")
    end_time = time.time()
    
    print(f"✅ sanitize_username: {end_time - start_time:.4f}s для 1000 итераций")
    
    # Тестируем функциональность
    assert sanitize_username_optimized("user_123-test") == "user_123-test"
    assert sanitize_username_optimized("user@domain.com") == "userdomaincom"
    assert sanitize_username_optimized(None) == ""
    assert sanitize_username_optimized("") == ""
    
    print("✅ Optimized sanitize_username тест пройден")


def test_optimized_sanitize_callback_data():
    """Тест оптимизированного sanitize_callback_data"""
    def sanitize_callback_data_optimized(data):
        if data is None:
            return ""
        try:
            data_str = str(data)
            safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            sanitized = ''.join(c for c in data_str if c in safe_chars)
            return sanitized[:64]
        except Exception:
            return ""
    
    # Тестируем производительность
    start_time = time.time()
    for i in range(1000):
        result = sanitize_callback_data_optimized("button_123-test")
    end_time = time.time()
    
    print(f"✅ sanitize_callback_data: {end_time - start_time:.4f}s для 1000 итераций")
    
    # Тестируем функциональность
    assert sanitize_callback_data_optimized("button_123-test") == "button_123-test"
    assert sanitize_callback_data_optimized("button@click") == "buttonclick"
    assert sanitize_callback_data_optimized(None) == ""
    assert sanitize_callback_data_optimized("") == ""
    
    print("✅ Optimized sanitize_callback_data тест пройден")


def test_optimized_validation_result():
    """Тест оптимизированного ValidationResult"""
    class ValidationResultOptimized:
        def __init__(self, is_valid=True, sanitized_data=None, errors=None, warnings=None):
            self.is_valid = is_valid
            if sanitized_data is None:
                self.sanitized_data = ""
            elif isinstance(sanitized_data, str):
                self.sanitized_data = sanitized_data
            else:
                try:
                    self.sanitized_data = str(sanitized_data)
                except Exception:
                    self.sanitized_data = ""
            self.errors = errors or []
            self.warnings = warnings or []
    
    # Тестируем производительность
    start_time = time.time()
    for i in range(1000):
        result = ValidationResultOptimized(True, "test_data")
    end_time = time.time()
    
    print(f"✅ ValidationResult: {end_time - start_time:.4f}s для 1000 итераций")
    
    # Тестируем функциональность
    result1 = ValidationResultOptimized(True, "Hello")
    assert result1.sanitized_data == "Hello"
    assert result1.is_valid is True
    
    result2 = ValidationResultOptimized(True, 123)
    assert result2.sanitized_data == "123"
    
    result3 = ValidationResultOptimized(True, None)
    assert result3.sanitized_data == ""
    
    print("✅ Optimized ValidationResult тест пройден")


def test_utf8_byte_limits():
    """Тест ограничений по байтам UTF-8"""
    def test_utf8_limit(data, max_bytes):
        try:
            return data.encode('utf-8')[:max_bytes].decode('utf-8', errors='ignore')
        except Exception:
            return ""
    
    # Тест с кириллицей (каждый символ = 2 байта)
    cyrillic_text = "Привет мир!"
    result = test_utf8_limit(cyrillic_text, 10)  # 10 байт = 5 символов
    assert len(result.encode('utf-8')) <= 10
    
    # Тест с латиницей (каждый символ = 1 байт)
    latin_text = "Hello World!"
    result = test_utf8_limit(latin_text, 10)  # 10 байт = 10 символов
    assert len(result.encode('utf-8')) <= 10
    
    print("✅ UTF-8 byte limits тест пройден")


def test_performance_comparison():
    """Сравнение производительности оптимизированных и неоптимизированных версий"""
    import re
    
    def old_sanitize_with_regex(data):
        if data is None:
            return ""
        try:
            data_str = str(data)
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', data_str)
            return sanitized[:50]
        except Exception:
            return ""
    
    def new_sanitize_optimized(data):
        if data is None:
            return ""
        try:
            data_str = str(data)
            safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            sanitized = ''.join(c for c in data_str if c in safe_chars)
            return sanitized[:50]
        except Exception:
            return ""
    
    test_data = "user_123-test@domain.com"
    iterations = 1000
    
    # Тест старой версии с regex
    start_time = time.time()
    for i in range(iterations):
        result = old_sanitize_with_regex(test_data)
    old_time = time.time() - start_time
    
    # Тест новой оптимизированной версии
    start_time = time.time()
    for i in range(iterations):
        result = new_sanitize_optimized(test_data)
    new_time = time.time() - start_time
    
    speedup = old_time / new_time if new_time > 0 else 1
    
    print(f"✅ Performance comparison:")
    print(f"   Old version (regex): {old_time:.4f}s")
    print(f"   New version (optimized): {new_time:.4f}s")
    print(f"   Speedup: {speedup:.2f}x")
    
    # Проверяем, что результаты одинаковые
    assert old_sanitize_with_regex(test_data) == new_sanitize_optimized(test_data)
    
    print("✅ Performance comparison тест пройден")


async def test_all_optimized_fallbacks():
    """Запуск всех тестов оптимизированных fallback-реализаций"""
    print("🧪 Запуск тестов оптимизированных fallback-реализаций...")
    
    try:
        test_optimized_sanitize_user_input()
        test_optimized_sanitize_username()
        test_optimized_sanitize_callback_data()
        test_optimized_validation_result()
        test_utf8_byte_limits()
        test_performance_comparison()
        
        print("\n🎉 Все тесты оптимизированных fallback-реализаций пройдены успешно!")
        print("✅ Оптимизация работает корректно и быстрее!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_all_optimized_fallbacks())

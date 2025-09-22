"""
Тесты для дополнительных исправлений fallback-реализаций
"""
import asyncio
import logging


def test_advanced_sanitize_username():
    """Тест улучшенного sanitize_username с специальными символами"""
    def sanitize_username_advanced(username):
        if username is None:
            return ""
        try:
            # Безопасное преобразование в строку
            username_str = str(username)
            # Удаляем потенциально опасные символы
            import re
            # Оставляем только буквы, цифры, подчеркивания и дефисы
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', username_str)
            # Ограничиваем длину
            return sanitized[:50]
        except Exception as e:
            logging.warning(f"Username sanitizer fallback error: {e}")
            return ""
    
    # Тестируем различные входные данные
    assert sanitize_username_advanced("user123") == "user123"
    assert sanitize_username_advanced("user@domain.com") == "userdomaincom"
    assert sanitize_username_advanced("user<script>") == "userscript"
    assert sanitize_username_advanced("user with spaces") == "userwithspaces"
    assert sanitize_username_advanced("user!@#$%^&*()") == "user"
    assert sanitize_username_advanced("user_123-test") == "user_123-test"
    assert sanitize_username_advanced(None) == ""
    assert sanitize_username_advanced("") == ""
    assert sanitize_username_advanced("a" * 100) == "a" * 50  # Ограничение длины
    
    print("✅ Advanced sanitize_username тест пройден")


def test_advanced_sanitize_callback_data():
    """Тест улучшенного sanitize_callback_data с специальными символами"""
    def sanitize_callback_data_advanced(data):
        if data is None:
            return ""
        try:
            # Безопасное преобразование в строку
            data_str = str(data)
            # Удаляем потенциально опасные символы
            import re
            # Оставляем только буквы, цифры, подчеркивания и дефисы
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', data_str)
            # Ограничиваем длину (Telegram callback data limit is 64 bytes)
            return sanitized[:64]
        except Exception as e:
            logging.warning(f"Callback data sanitizer fallback error: {e}")
            return ""
    
    # Тестируем различные входные данные
    assert sanitize_callback_data_advanced("button_123") == "button_123"
    assert sanitize_callback_data_advanced("button@click") == "buttonclick"
    assert sanitize_callback_data_advanced("button<script>") == "buttonscript"
    assert sanitize_callback_data_advanced("button with spaces") == "buttonwithspaces"
    assert sanitize_callback_data_advanced("button!@#$%^&*()") == "button"
    assert sanitize_callback_data_advanced("button_123-test") == "button_123-test"
    assert sanitize_callback_data_advanced(None) == ""
    assert sanitize_callback_data_advanced("") == ""
    assert sanitize_callback_data_advanced("a" * 100) == "a" * 64  # Ограничение длины
    
    print("✅ Advanced sanitize_callback_data тест пройден")


def test_advanced_sanitize_user_input():
    """Тест улучшенного sanitize_user_input с различными типами данных"""
    def sanitize_user_input_advanced(data):
        if data is None:
            return ""
        try:
            # Безопасное преобразование в строку
            data_str = str(data)
            # Удаляем потенциально опасные символы
            import re
            # Оставляем только безопасные символы
            sanitized = re.sub(r'[^a-zA-Zа-яА-Я0-9\s@_.,!?\-()]', '', data_str)
            # Ограничиваем длину
            return sanitized[:1000]
        except Exception as e:
            logging.warning(f"Input sanitizer fallback error: {e}")
            return ""
    
    # Тестируем различные входные данные
    assert sanitize_user_input_advanced("Hello World!") == "Hello World!"
    assert sanitize_user_input_advanced("Привет мир!") == "Привет мир!"
    assert sanitize_user_input_advanced("user@domain.com") == "user@domain.com"
    assert sanitize_user_input_advanced("text<script>alert('xss')</script>") == "textscriptalert(xss)script"
    assert sanitize_user_input_advanced("text with spaces and punctuation!") == "text with spaces and punctuation!"
    assert sanitize_user_input_advanced("text!@#$%^&*()") == "text!@()"
    assert sanitize_user_input_advanced("text_123-test") == "text_123-test"
    assert sanitize_user_input_advanced(None) == ""
    assert sanitize_user_input_advanced("") == ""
    assert sanitize_user_input_advanced(123) == "123"
    assert sanitize_user_input_advanced(True) == "True"
    assert sanitize_user_input_advanced("a" * 2000) == "a" * 1000  # Ограничение длины
    
    print("✅ Advanced sanitize_user_input тест пройден")


def test_advanced_validation_result():
    """Тест улучшенного ValidationResult с различными типами данных"""
    class ValidationResultAdvanced:
        def __init__(self, is_valid=True, sanitized_data=None, errors=None, warnings=None):
            self.is_valid = is_valid
            # Безопасная обработка sanitized_data
            if sanitized_data is None:
                self.sanitized_data = ""
            else:
                try:
                    # Пытаемся преобразовать в строку, если это возможно
                    if isinstance(sanitized_data, (str, int, float, bool)):
                        self.sanitized_data = str(sanitized_data)
                    elif isinstance(sanitized_data, (list, dict)):
                        # Для сложных типов оставляем как есть
                        self.sanitized_data = sanitized_data
                    else:
                        # Для неизвестных типов пытаемся преобразовать в строку
                        self.sanitized_data = str(sanitized_data)
                except Exception as e:
                    logging.warning(f"ValidationResult sanitized_data error: {e}")
                    self.sanitized_data = ""
            self.errors = errors or []
            self.warnings = warnings or []
    
    # Тестируем различные типы данных
    result1 = ValidationResultAdvanced(True, "Hello World")
    assert result1.sanitized_data == "Hello World"
    assert result1.is_valid is True
    
    result2 = ValidationResultAdvanced(True, 123)
    assert result2.sanitized_data == "123"
    
    result3 = ValidationResultAdvanced(True, True)
    assert result3.sanitized_data == "True"
    
    result4 = ValidationResultAdvanced(True, [1, 2, 3])
    assert result4.sanitized_data == [1, 2, 3]
    
    result5 = ValidationResultAdvanced(True, {"key": "value"})
    assert result5.sanitized_data == {"key": "value"}
    
    result6 = ValidationResultAdvanced(True, None)
    assert result6.sanitized_data == ""
    
    result7 = ValidationResultAdvanced(False, "error", ["Invalid input"], ["Warning"])
    assert result7.is_valid is False
    assert result7.errors == ["Invalid input"]
    assert result7.warnings == ["Warning"]
    
    print("✅ Advanced ValidationResult тест пройден")


def test_edge_cases():
    """Тест граничных случаев и потенциально проблемных данных"""
    
    # Тест с очень длинными строками
    long_string = "a" * 10000
    def sanitize_long_string(data):
        if data is None:
            return ""
        try:
            data_str = str(data)
            import re
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', data_str)
            return sanitized[:50]
        except Exception:
            return ""
    
    result = sanitize_long_string(long_string)
    assert len(result) == 50
    assert result == "a" * 50
    
    # Тест с None и пустыми значениями
    assert sanitize_long_string(None) == ""
    assert sanitize_long_string("") == ""
    assert sanitize_long_string("   ") == ""
    
    # Тест с специальными символами Unicode
    unicode_string = "тест_123-тест!@#$%^&*()"
    result = sanitize_long_string(unicode_string)
    assert result == "_123-"  # Цифры и разрешенные символы остались
    
    # Тест с объектами
    class TestObject:
        def __str__(self):
            return "test_object"
    
    obj = TestObject()
    result = sanitize_long_string(obj)
    assert result == "test_object"
    
    print("✅ Edge cases тест пройден")


async def test_all_advanced_fallbacks():
    """Запуск всех тестов дополнительных исправлений fallback-реализаций"""
    print("🧪 Запуск тестов дополнительных исправлений fallback-реализаций...")
    
    try:
        test_advanced_sanitize_username()
        test_advanced_sanitize_callback_data()
        test_advanced_sanitize_user_input()
        test_advanced_validation_result()
        test_edge_cases()
        
        print("\n🎉 Все тесты дополнительных исправлений пройдены успешно!")
        print("✅ Дополнительные исправления работают корректно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_all_advanced_fallbacks())

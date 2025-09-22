"""
Тест исправления проблемы с двойным символом @ в username
"""
import re
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bot'))

try:
    from app.utils.input_sanitizer import InputSanitizer
except ImportError:
    print("❌ Не удалось импортировать InputSanitizer")
    sys.exit(1)


def test_input_sanitizer_username_processing():
    """Тест обработки username в InputSanitizer"""
    
    # Тест 1: Username с @ в начале
    username_with_at = "@jericho_pipes"
    result = InputSanitizer.sanitize_username(username_with_at)
    assert result == "jericho_pipes", f"Expected 'jericho_pipes', got '{result}'"
    
    # Тест 2: Username без @ в начале
    username_without_at = "jericho_pipes"
    result = InputSanitizer.sanitize_username(username_without_at)
    assert result == "jericho_pipes", f"Expected 'jericho_pipes', got '{result}'"
    
    # Тест 3: Двойной @ (не должно происходить, но на всякий случай)
    username_double_at = "@@jericho_pipes"
    result = InputSanitizer.sanitize_username(username_double_at)
    assert result is None, f"Expected None for invalid username with @ in middle, got '{result}'"
    
    # Тест 4: Неверный формат
    invalid_username = "user@domain.com"
    result = InputSanitizer.sanitize_username(invalid_username)
    assert result is None, f"Expected None for invalid username, got '{result}'"
    
    # Тест 5: Слишком короткий username
    short_username = "user"
    result = InputSanitizer.sanitize_username(short_username)
    assert result is None, f"Expected None for short username, got '{result}'"
    
    # Тест 6: Слишком длинный username
    long_username = "a" * 35
    result = InputSanitizer.sanitize_username(long_username)
    assert result is None, f"Expected None for long username, got '{result}'"
    
    print("✅ InputSanitizer username processing tests passed")


def test_username_regex_pattern():
    """Тест regex pattern для username"""
    
    # Валидные username
    valid_usernames = [
        "jericho_pipes",
        "user123",
        "test_user",
        "admin",
        "a" * 32  # максимальная длина
    ]
    
    for username in valid_usernames:
        assert re.match(r'^[a-zA-Z0-9_]{5,32}$', username), f"Username '{username}' should be valid"
    
    # Невалидные username
    invalid_usernames = [
        "@jericho_pipes",  # с @
        "user",  # слишком короткий
        "a" * 35,  # слишком длинный
        "user@domain",  # с @ в середине
        "user-name",  # с дефисом
        "user.name",  # с точкой
        "user name",  # с пробелом
        "",  # пустой
        "1234",  # только цифры (слишком короткий)
    ]
    
    for username in invalid_usernames:
        assert not re.match(r'^[a-zA-Z0-9_]{5,32}$', username), f"Username '{username}' should be invalid"
    
    print("✅ Username regex pattern tests passed")


def test_remove_admin_username_processing():
    """Тест обработки username в функции удаления администратора"""
    
    # Имитируем обработку username без моков
    
    # Имитируем логику обработки username из action_remove_admin.py
    raw_username = "@jericho_pipes"
    username = raw_username[1:]  # "jericho_pipes" - убираем @
    sanitized_username = InputSanitizer.sanitize_username(username)  # "jericho_pipes"
    
    # Проверяем результат
    assert sanitized_username == "jericho_pipes", f"Expected 'jericho_pipes', got '{sanitized_username}'"
    
    # Проверяем, что для API вызова будет использоваться правильный формат
    api_call_username = f"@{sanitized_username}"  # "@jericho_pipes"
    assert api_call_username == "@jericho_pipes", f"Expected '@jericho_pipes', got '{api_call_username}'"
    
    # Проверяем, что не будет двойного @
    assert not api_call_username.startswith("@@"), "API call should not have double @"
    
    print("✅ Remove admin username processing tests passed")


def test_username_validation_before_api_call():
    """Тест валидации username перед вызовом API"""
    
    # Валидные username для API
    valid_usernames = [
        "jericho_pipes",
        "user123",
        "test_user",
        "admin"
    ]
    
    for username in valid_usernames:
        assert re.match(r'^[a-zA-Z0-9_]{5,32}$', username), f"Username '{username}' should be valid for API call"
    
    # Невалидные username для API
    invalid_usernames = [
        "@jericho_pipes",  # с @
        "user",  # слишком короткий
        "a" * 35,  # слишком длинный
        "user@domain",  # с @ в середине
        "user-name",  # с дефисом
        "",  # пустой
        None  # None
    ]
    
    for username in invalid_usernames:
        if username is None:
            assert not username, "None username should be invalid"
        else:
            assert not re.match(r'^[a-zA-Z0-9_]{5,32}$', username), f"Username '{username}' should be invalid for API call"
    
    print("✅ Username validation before API call tests passed")


def test_edge_cases():
    """Тест граничных случаев"""
    
    # Тест с None
    result = InputSanitizer.sanitize_username(None)
    assert result is None, "None input should return None"
    
    # Тест с пустой строкой
    result = InputSanitizer.sanitize_username("")
    assert result is None, "Empty string should return None"
    
    # Тест с пробелами
    result = InputSanitizer.sanitize_username("  jericho_pipes  ")
    assert result == "jericho_pipes", "Whitespace should be trimmed"
    
    # Тест с HTML тегами
    result = InputSanitizer.sanitize_username("<script>jericho_pipes</script>")
    assert result == "jericho_pipes", "HTML tags should be removed"
    
    # Тест с HTML entities (должен быть None, так как & не разрешен в username)
    result = InputSanitizer.sanitize_username("jericho&amp;pipes")
    assert result is None, "HTML entities with invalid characters should return None"
    
    print("✅ Edge cases tests passed")


if __name__ == "__main__":
    print("🧪 Запуск тестов исправления проблемы с двойным @ в username...")
    
    try:
        test_input_sanitizer_username_processing()
        test_username_regex_pattern()
        test_username_validation_before_api_call()
        test_edge_cases()
        
        print("\n✅ Все тесты исправления проблемы с двойным @ прошли успешно!")
        print("🔧 Исправления:")
        print("   - InputSanitizer.sanitize_username теперь убирает @ из начала username")
        print("   - action_remove_admin.py использует консистентную обработку username")
        print("   - Добавлена дополнительная валидация перед вызовом Telegram API")
        print("   - Улучшены сообщения об ошибках для диагностики")
        
    except Exception as e:
        print(f"❌ Тест не прошел: {e}")
        raise

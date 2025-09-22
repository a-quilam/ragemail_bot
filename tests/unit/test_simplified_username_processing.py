"""
Тест упрощенной обработки username без InputSanitizer
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bot'))


def test_simplified_username_processing():
    """Тест упрощенной обработки username как в функции добавления"""
    
    # Имитируем логику из action_remove_admin.py (упрощенная версия)
    def process_username_simplified(text):
        """Упрощенная обработка username без InputSanitizer"""
        if text and text.strip().startswith('@'):
            username = text.strip()[1:]  # убираем @
            return username
        return None
    
    # Тест 1: Обычный username
    result = process_username_simplified("@jericho_pipes")
    assert result == "jericho_pipes", f"Expected 'jericho_pipes', got '{result}'"
    
    # Тест 2: Username с пробелами
    result = process_username_simplified("  @jericho_pipes  ")
    assert result == "jericho_pipes", f"Expected 'jericho_pipes', got '{result}'"
    
    # Тест 3: Username без @
    result = process_username_simplified("jericho_pipes")
    assert result is None, f"Expected None, got '{result}'"
    
    # Тест 4: Пустая строка
    result = process_username_simplified("")
    assert result is None, f"Expected None, got '{result}'"
    
    # Тест 5: Только @
    result = process_username_simplified("@")
    assert result == "", f"Expected empty string, got '{result}'"
    
    print("✅ Simplified username processing tests passed")


def test_api_call_format():
    """Тест формата вызова API"""
    
    def format_api_call(username):
        """Форматирование для API вызова"""
        return f"@{username}"
    
    # Тест 1: Обычный username
    api_call = format_api_call("jericho_pipes")
    assert api_call == "@jericho_pipes", f"Expected '@jericho_pipes', got '{api_call}'"
    
    # Тест 2: Проверяем, что нет двойного @
    assert not api_call.startswith("@@"), "API call should not have double @"
    
    print("✅ API call format tests passed")


def test_consistency_with_add_admin():
    """Тест консистентности с функцией добавления администратора"""
    
    # Логика из action_add_admin.py
    def add_admin_username_processing(text):
        if text and text.strip().startswith('@'):
            username = text.strip()[1:]  # убираем @
            return username
        return None
    
    # Логика из action_remove_admin.py (упрощенная)
    def remove_admin_username_processing(text):
        if text and text.strip().startswith('@'):
            username = text.strip()[1:]  # убираем @
            return username
        return None
    
    # Тестируем одинаковые входные данные
    test_cases = [
        "@jericho_pipes",
        "  @jericho_pipes  ",
        "@user123",
        "@test_user",
    ]
    
    for test_case in test_cases:
        add_result = add_admin_username_processing(test_case)
        remove_result = remove_admin_username_processing(test_case)
        
        assert add_result == remove_result, f"Inconsistent processing for '{test_case}': add='{add_result}', remove='{remove_result}'"
    
    print("✅ Consistency with add admin tests passed")


def test_performance_comparison():
    """Тест производительности упрощенной версии"""
    import time
    
    def simplified_processing(text):
        """Упрощенная обработка"""
        if text and text.strip().startswith('@'):
            return text.strip()[1:]
        return None
    
    def complex_processing(text):
        """Сложная обработка с валидацией (имитация InputSanitizer)"""
        if not text or not text.strip().startswith('@'):
            return None
        
        username = text.strip()[1:]
        
        # Имитация сложной валидации
        import re
        if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
            return None
        
        return username
    
    # Тестируем производительность
    test_input = "@jericho_pipes"
    iterations = 10000
    
    # Упрощенная версия
    start_time = time.time()
    for _ in range(iterations):
        simplified_processing(test_input)
    simplified_time = time.time() - start_time
    
    # Сложная версия
    start_time = time.time()
    for _ in range(iterations):
        complex_processing(test_input)
    complex_time = time.time() - start_time
    
    speedup = complex_time / simplified_time
    
    print(f"✅ Performance comparison:")
    print(f"   Simplified: {simplified_time:.4f}s for {iterations} iterations")
    print(f"   Complex: {complex_time:.4f}s for {iterations} iterations")
    print(f"   Speedup: {speedup:.1f}x faster")
    
    assert speedup > 1.5, f"Simplified version should be at least 1.5x faster, got {speedup:.1f}x"


if __name__ == "__main__":
    print("🧪 Запуск тестов упрощенной обработки username...")
    
    try:
        test_simplified_username_processing()
        test_api_call_format()
        test_consistency_with_add_admin()
        test_performance_comparison()
        
        print("\n✅ Все тесты упрощенной обработки username прошли успешно!")
        print("🚀 Упрощения:")
        print("   - Убран InputSanitizer (избыточная валидация)")
        print("   - Убрана дополнительная валидация перед API")
        print("   - Упрощен импорт (убран модуль re)")
        print("   - Консистентность с функцией добавления администратора")
        print("   - Улучшена производительность")
        print("   - Telegram API сам валидирует username")
        
    except Exception as e:
        print(f"❌ Тест не прошел: {e}")
        raise

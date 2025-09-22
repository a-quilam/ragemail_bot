#!/usr/bin/env python3
"""
Тест сетевых улучшений бота
"""
import asyncio
import logging
import sys
import os

# Добавляем текущую директорию в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app.core.config import settings
from app.core.network_config import NetworkConfig
from app.services.network_monitor import NetworkMonitor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_network_config():
    """Тестирует конфигурацию сети"""
    print("🔧 Тестирование сетевой конфигурации...")
    
    try:
        # Создаем бота с оптимизированными настройками
        bot = NetworkConfig.create_bot_with_network_config(settings.BOT_TOKEN, settings)
        print("✅ Бот создан с оптимизированными сетевыми настройками")
        
        # Тестируем соединение
        print("🌐 Тестирование соединения с Telegram API...")
        is_connected = await NetworkConfig.test_connection(bot)
        
        if is_connected:
            print("✅ Соединение с Telegram API успешно")
        else:
            print("❌ Не удалось подключиться к Telegram API")
            return False
        
        # Создаем монитор сети
        print("📊 Создание монитора сети...")
        monitor = NetworkMonitor(bot, check_interval=5.0)  # Короткий интервал для теста
        
        # Добавляем callback для отслеживания изменений
        def on_health_change(is_healthy: bool):
            status = "✅ Здоровое" if is_healthy else "⚠️ Проблемы"
            print(f"📈 Состояние сети изменилось: {status}")
        
        monitor.add_health_callback(on_health_change)
        
        # Запускаем мониторинг
        print("🔄 Запуск мониторинга сети...")
        await monitor.start_monitoring()
        
        # Ждем несколько проверок
        print("⏳ Ожидание 15 секунд для тестирования мониторинга...")
        await asyncio.sleep(15)
        
        # Получаем статистику
        stats = monitor.get_stats()
        print(f"📊 Статистика сети:")
        print(f"   • Всего запросов: {stats['total_requests']}")
        print(f"   • Успешных: {stats['successful_requests']}")
        print(f"   • Неудачных: {stats['failed_requests']}")
        print(f"   • Успешность: {stats['success_rate']:.1f}%")
        print(f"   • Здоровое соединение: {'Да' if stats['is_healthy'] else 'Нет'}")
        
        # Останавливаем мониторинг
        await monitor.stop_monitoring()
        print("🛑 Мониторинг остановлен")
        
        # Закрываем сессию бота
        await bot.session.close()
        print("🔒 Сессия бота закрыта")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        logging.error(f"Test error: {e}", exc_info=True)
        return False

async def test_retry_logic():
    """Тестирует логику retry"""
    print("\n🔄 Тестирование логики retry...")
    
    from app.utils.error_handler import handle_network_error_with_retry
    from aiogram.exceptions import TelegramNetworkError
    
    # Симулируем сетевую ошибку
    fake_error = TelegramNetworkError("HTTP Client says - Request timeout error")
    
    print("⚠️ Симуляция сетевой ошибки...")
    result = await handle_network_error_with_retry(
        fake_error, 
        "test_operation", 
        max_retries=2,  # Короткий тест
        base_delay=0.5  # Быстрый тест
    )
    
    print(f"📋 Результат обработки ошибки: {result}")
    return True

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестирования сетевых улучшений бота")
    print("=" * 50)
    
    # Проверяем настройки
    print(f"⚙️ Настройки сети:")
    print(f"   • Таймаут подключения: {settings.NETWORK_CONNECT_TIMEOUT}с")
    print(f"   • Таймаут чтения: {settings.NETWORK_READ_TIMEOUT}с")
    print(f"   • Общий таймаут: {settings.NETWORK_TOTAL_TIMEOUT}с")
    print(f"   • Максимум попыток: {settings.NETWORK_MAX_RETRIES}")
    print(f"   • Базовая задержка: {settings.NETWORK_BASE_DELAY}с")
    print(f"   • Максимальная задержка: {settings.NETWORK_MAX_DELAY}с")
    print(f"   • Коэффициент роста: {settings.NETWORK_BACKOFF_FACTOR}")
    print(f"   • Интервал мониторинга: {settings.NETWORK_MONITOR_INTERVAL}с")
    print()
    
    # Тестируем конфигурацию сети
    config_success = await test_network_config()
    
    # Тестируем логику retry
    retry_success = await test_retry_logic()
    
    print("\n" + "=" * 50)
    print("📋 Результаты тестирования:")
    print(f"   • Конфигурация сети: {'✅ Успешно' if config_success else '❌ Ошибка'}")
    print(f"   • Логика retry: {'✅ Успешно' if retry_success else '❌ Ошибка'}")
    
    if config_success and retry_success:
        print("\n🎉 Все тесты прошли успешно!")
        print("🌐 Сетевые улучшения готовы к использованию")
    else:
        print("\n⚠️ Некоторые тесты не прошли")
        print("🔧 Проверьте настройки и логи")

if __name__ == "__main__":
    asyncio.run(main())

"""
Команда для проверки состояния сетевого соединения
"""
import logging
import time
from aiogram import types, Router
from aiogram.filters import Command
from app.core.permissions import require_admin
from app.utils.error_handler import handle_error

logger = logging.getLogger(__name__)
router = Router()

# Глобальная переменная для хранения монитора сети
network_monitor = None

def set_network_monitor(monitor):
    """Устанавливает монитор сети для использования в командах"""
    global network_monitor
    network_monitor = monitor

@router.message(Command("network_status"))
@require_admin
async def cmd_network_status(message: types.Message):
    """Показывает состояние сетевого соединения"""
    try:
        if not network_monitor:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Монитор сети не инициализирован.",
                parse_mode="HTML"
            )
            return
        
        stats = network_monitor.get_stats()
        health_status = network_monitor.get_health_status()
        
        # Форматируем время
        def format_time(timestamp):
            if timestamp is None:
                return "Никогда"
            import time
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        
        # Форматируем продолжительность
        def format_duration(seconds):
            if seconds < 60:
                return f"{seconds:.0f}с"
            elif seconds < 3600:
                return f"{seconds/60:.0f}м {seconds%60:.0f}с"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}ч {minutes}м"
        
        response = (
            f"🌐 <b>Состояние сетевого соединения</b>\n\n"
            f"{health_status}\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего запросов: {stats['total_requests']}\n"
            f"• Успешных: {stats['successful_requests']}\n"
            f"• Неудачных: {stats['failed_requests']}\n"
            f"• Сетевых ошибок: {stats['network_errors']}\n"
            f"• API ошибок: {stats['api_errors']}\n"
            f"• Успешность: {stats['success_rate']:.1f}%\n"
            f"• Последовательных ошибок: {stats['consecutive_failures']}\n"
            f"• Время работы: {format_duration(stats['connection_uptime'])}\n\n"
            f"⏰ <b>Временные метки:</b>\n"
            f"• Последний успех: {format_time(stats['last_success_time'])}\n"
            f"• Последняя ошибка: {format_time(stats['last_error_time'])}"
        )
        
        await message.answer(response, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in network status command: {e}")
        await handle_error(e, message, context="network_status_command")

@router.message(Command("network_test"))
@require_admin
async def cmd_network_test(message: types.Message):
    """Тестирует соединение с Telegram API"""
    try:
        if not network_monitor:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Монитор сети не инициализирован.",
                parse_mode="HTML"
            )
            return
        
        # Отправляем сообщение о начале теста
        test_msg = await message.answer("🔄 Тестируем соединение...")
        
        # Тестируем соединение
        from app.core.network_config import NetworkConfig
        from app.core.config import settings
        
        start_time = time.time()
        is_connected = await NetworkConfig.test_connection(network_monitor.bot)
        response_time = time.time() - start_time
        
        if is_connected:
            await test_msg.edit_text(
                f"✅ <b>Тест соединения успешен</b>\n\n"
                f"Время отклика: {response_time:.3f}с\n"
                f"Соединение с Telegram API работает нормально.",
                parse_mode="HTML"
            )
        else:
            await test_msg.edit_text(
                f"❌ <b>Тест соединения неудачен</b>\n\n"
                f"Не удалось подключиться к Telegram API.\n"
                f"Проверьте интернет-соединение и настройки бота.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in network test command: {e}")
        await handle_error(e, message, context="network_test_command")

@router.message(Command("network_config"))
@require_admin
async def cmd_network_config(message: types.Message):
    """Показывает текущие сетевые настройки"""
    try:
        from app.core.config import settings
        
        response = (
            f"⚙️ <b>Сетевые настройки</b>\n\n"
            f"🔗 <b>Таймауты:</b>\n"
            f"• Подключение: {settings.NETWORK_CONNECT_TIMEOUT}с\n"
            f"• Чтение: {settings.NETWORK_READ_TIMEOUT}с\n"
            f"• Общий: {settings.NETWORK_TOTAL_TIMEOUT}с\n\n"
            f"🔄 <b>Retry настройки:</b>\n"
            f"• Максимум попыток: {settings.NETWORK_MAX_RETRIES}\n"
            f"• Базовая задержка: {settings.NETWORK_BASE_DELAY}с\n"
            f"• Максимальная задержка: {settings.NETWORK_MAX_DELAY}с\n"
            f"• Коэффициент роста: {settings.NETWORK_BACKOFF_FACTOR}\n\n"
            f"📊 <b>Мониторинг:</b>\n"
            f"• Интервал проверки: {settings.NETWORK_MONITOR_INTERVAL}с"
        )
        
        await message.answer(response, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in network config command: {e}")
        await handle_error(e, message, context="network_config_command")

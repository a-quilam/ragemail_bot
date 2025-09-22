#!/usr/bin/env python3
"""
Скрипт запуска бота с правильными путями
"""
import sys
import os
import asyncio
import logging

# Добавляем текущую директорию в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Убеждаемся, что app модуль доступен
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

async def main():
    """Главная функция запуска бота"""
    try:
        # Проверяем, что модуль app доступен
        try:
            import app
            print(f'✅ Модуль app найден в: {app.__file__}')
        except ImportError as e:
            print(f'❌ Не удалось импортировать модуль app: {e}')
            print(f'📁 Текущая директория: {current_dir}')
            print(f'📁 PYTHONPATH: {sys.path[:3]}')
            return
        
        from app.main import main as bot_main
        print('🚀 Запускаем бота...')
        await bot_main()
    except KeyboardInterrupt:
        print('⏹️ Бот остановлен пользователем')
    except Exception as e:
        print(f'❌ Ошибка запуска бота: {e}')
        logging.error(f"Bot startup error: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    asyncio.run(main())

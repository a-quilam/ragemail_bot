#!/bin/bash
# Скрипт запуска бота

echo "🚀 Запускаем бота..."

# Переходим в директорию бота
cd "$(dirname "$0")"

# Активируем виртуальное окружение
source venv/bin/activate

# Устанавливаем PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Запускаем бота
python run_bot.py

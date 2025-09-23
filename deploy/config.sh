#!/bin/bash

# Конфигурационный файл для развертывания
# Создайте этот файл и укажите IP вашего сервера

# IP адрес вашего сервера
# Замените на IP вашего сервера, например: SERVER_IP="192.168.1.100"
SERVER_IP=""

# Пользователь для подключения к серверу (обычно root)
SERVER_USER="root"

# Пользователь для запуска бота на сервере
BOT_USER="botuser"

# Директория проекта на сервере
PROJECT_DIR="/home/$BOT_USER/ragemail_bot"

# Локальная директория для бэкапов
LOCAL_BACKUP_DIR="./backups"

# Проверка конфигурации
check_config() {
    if [ -z "$SERVER_IP" ]; then
        echo "❌ Ошибка: SERVER_IP не указан в config.sh"
        echo "📝 Отредактируйте файл deploy/config.sh и укажите IP вашего сервера"
        echo "   Пример: SERVER_IP=\"192.168.1.100\""
        exit 1
    fi
}

# Загрузка токена из .env
load_bot_token() {
    if [ -f "bot/.env" ]; then
        BOT_TOKEN=$(grep "^BOT_TOKEN=" bot/.env | cut -d'=' -f2)
        if [ -z "$BOT_TOKEN" ]; then
            echo "❌ Ошибка: BOT_TOKEN не найден в bot/.env"
            exit 1
        fi
        echo "✅ Токен бота загружен из bot/.env"
    else
        echo "❌ Ошибка: Файл bot/.env не найден"
        exit 1
    fi
}

#!/bin/bash

# Скрипт первоначальной настройки
# Помогает настроить IP сервера и проверить конфигурацию

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функции для вывода
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🚀 Настройка развертывания Telegram-бота"
echo "=========================================="

# Проверяем наличие .env файла
if [ ! -f "bot/.env" ]; then
    error "Файл bot/.env не найден!"
    echo "Создайте файл bot/.env с вашим токеном бота:"
    echo "BOT_TOKEN=your_bot_token_here"
    exit 1
fi

# Проверяем токен бота
BOT_TOKEN=$(grep "^BOT_TOKEN=" bot/.env | cut -d'=' -f2)
if [ -z "$BOT_TOKEN" ]; then
    error "BOT_TOKEN не найден в bot/.env"
    exit 1
fi

success "Токен бота найден: ${BOT_TOKEN:0:10}..."

# Проверяем config.sh
if [ ! -f "deploy/config.sh" ]; then
    error "Файл deploy/config.sh не найден!"
    exit 1
fi

# Читаем текущий IP сервера
CURRENT_IP=$(grep "^SERVER_IP=" deploy/config.sh | cut -d'"' -f2)

if [ -z "$CURRENT_IP" ]; then
    echo ""
    log "IP сервера не настроен в deploy/config.sh"
    echo ""
    echo "Введите IP адрес вашего сервера:"
    read -p "IP сервера: " SERVER_IP
    
    if [ -z "$SERVER_IP" ]; then
        error "IP сервера не может быть пустым"
        exit 1
    fi
    
    # Обновляем config.sh
    sed -i.bak "s/^SERVER_IP=\"\"/SERVER_IP=\"$SERVER_IP\"/" deploy/config.sh
    success "IP сервера сохранен: $SERVER_IP"
else
    echo ""
    log "Текущий IP сервера: $CURRENT_IP"
    echo ""
    echo "Хотите изменить IP сервера? (y/n)"
    read -p "Ответ: " CHANGE_IP
    
    if [ "$CHANGE_IP" = "y" ] || [ "$CHANGE_IP" = "Y" ]; then
        echo ""
        echo "Введите новый IP адрес сервера:"
        read -p "IP сервера: " NEW_IP
        
        if [ -z "$NEW_IP" ]; then
            error "IP сервера не может быть пустым"
            exit 1
        fi
        
        # Обновляем config.sh
        sed -i.bak "s/^SERVER_IP=\"$CURRENT_IP\"/SERVER_IP=\"$NEW_IP\"/" deploy/config.sh
        success "IP сервера обновлен: $NEW_IP"
    fi
fi

# Загружаем обновленную конфигурацию
source deploy/config.sh

# Проверяем подключение к серверу
echo ""
log "Проверяем подключение к серверу $SERVER_IP..."

if ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_USER@$SERVER_IP exit 2>/dev/null; then
    success "Подключение к серверу установлено"
else
    warning "Не удается подключиться к серверу $SERVER_IP"
    echo ""
    echo "Возможные причины:"
    echo "1. Сервер недоступен"
    echo "2. SSH ключи не настроены"
    echo "3. Неправильный IP адрес"
    echo ""
    echo "Для настройки SSH ключей выполните:"
    echo "ssh-keygen -t rsa -b 4096"
    echo "ssh-copy-id $SERVER_USER@$SERVER_IP"
    echo ""
    echo "Продолжить настройку? (y/n)"
    read -p "Ответ: " CONTINUE
    
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 1
    fi
fi

# Проверяем права на выполнение скриптов
echo ""
log "Проверяем права на выполнение скриптов..."
chmod +x deploy/*.sh
success "Права на выполнение установлены"

# Показываем следующую команду
echo ""
echo "=========================================="
echo "🎉 Настройка завершена!"
echo "=========================================="
echo ""
echo "Теперь вы можете развернуть бота командой:"
echo ""
echo "  ./deploy/deploy_smart.sh"
echo ""
echo "Или проверить статус:"
echo ""
echo "  ./deploy/monitor_smart.sh"
echo ""
echo "Или создать резервную копию:"
echo ""
echo "  ./deploy/backup_smart.sh"
echo ""
echo "🚀 Удачи с развертыванием!"

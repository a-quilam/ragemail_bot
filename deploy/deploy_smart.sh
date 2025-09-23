#!/bin/bash

# Умный скрипт развертывания Telegram-бота
# Автоматически читает токен из .env и IP из config.sh

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

# Загружаем конфигурацию
source "$(dirname "$0")/config.sh"

# Проверяем конфигурацию
check_config

# Загружаем токен бота
load_bot_token

log "Начинаем развертывание бота на сервере $SERVER_IP"
log "Токен бота: ${BOT_TOKEN:0:10}..."

# Проверка подключения к серверу
log "Проверяем подключение к серверу..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_USER@$SERVER_IP exit 2>/dev/null; then
    error "Не удается подключиться к серверу $SERVER_IP"
    error "Убедитесь, что:"
    error "1. Сервер доступен"
    error "2. SSH ключи настроены"
    error "3. Пользователь $SERVER_USER существует"
    error ""
    error "Для настройки SSH ключей выполните:"
    error "ssh-keygen -t rsa -b 4096"
    error "ssh-copy-id $SERVER_USER@$SERVER_IP"
    exit 1
fi
success "Подключение к серверу установлено"

# Обновление системы
log "Обновляем систему..."
ssh $SERVER_USER@$SERVER_IP "apt update && apt upgrade -y"
success "Система обновлена"

# Установка необходимых пакетов
log "Устанавливаем необходимые пакеты..."
ssh $SERVER_USER@$SERVER_IP "apt install -y python3 python3-pip python3-venv git nginx supervisor curl"
success "Пакеты установлены"

# Создание пользователя для бота
log "Создаем пользователя $BOT_USER..."
if ssh $SERVER_USER@$SERVER_IP "id $BOT_USER" &>/dev/null; then
    warning "Пользователь $BOT_USER уже существует"
else
    ssh $SERVER_USER@$SERVER_IP "adduser --disabled-password --gecos '' $BOT_USER"
    ssh $SERVER_USER@$SERVER_IP "usermod -aG sudo $BOT_USER"
    success "Пользователь $BOT_USER создан"
fi

# Создание директории проекта
log "Создаем директорию проекта..."
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR"
success "Директория проекта создана"

# Клонирование репозитория
log "Клонируем репозиторий..."
if ssh $BOT_USER@$SERVER_IP "test -d $PROJECT_DIR/.git"; then
    warning "Репозиторий уже существует, обновляем..."
    ssh $BOT_USER@$SERVER_IP "cd $PROJECT_DIR && git pull origin main"
else
    # Нужно будет заменить на ваш реальный репозиторий
    warning "ВНИМАНИЕ: Замените URL репозитория в скрипте на ваш реальный!"
    ssh $BOT_USER@$SERVER_IP "cd /home/$BOT_USER && git clone https://github.com/your-username/ragemail_bot.git"
fi
success "Репозиторий обновлен"

# Настройка виртуального окружения
log "Настраиваем виртуальное окружение..."
ssh $BOT_USER@$SERVER_IP "cd $PROJECT_DIR/bot && python3 -m venv venv"
ssh $BOT_USER@$SERVER_IP "cd $PROJECT_DIR/bot && source venv/bin/activate && pip install --upgrade pip"
ssh $BOT_USER@$SERVER_IP "cd $PROJECT_DIR/bot && source venv/bin/activate && pip install -r requirements.txt"
success "Виртуальное окружение настроено"

# Создание .env файла на сервере
log "Создаем файл конфигурации на сервере..."
ssh $BOT_USER@$SERVER_IP "cat > $PROJECT_DIR/bot/.env << EOF
# Telegram Bot Token
BOT_TOKEN=$BOT_TOKEN

# База данных
DB_PATH=$PROJECT_DIR/bot/queue.db

# Логирование
LOG_LEVEL=INFO

# Часовой пояс
TIMEZONE=Europe/Moscow

# Сетевые настройки
NETWORK_MONITOR_INTERVAL=30
EOF"
success "Файл конфигурации создан на сервере"

# Создание директории для логов
log "Создаем директорию для логов..."
ssh $SERVER_USER@$SERVER_IP "mkdir -p /var/log/telegram-bot"
ssh $SERVER_USER@$SERVER_IP "chown $BOT_USER:$BOT_USER /var/log/telegram-bot"
success "Директория для логов создана"

# Копирование systemd сервиса
log "Настраиваем systemd сервис..."
scp deploy/telegram-bot.service $SERVER_USER@$SERVER_IP:/tmp/
ssh $SERVER_USER@$SERVER_IP "mv /tmp/telegram-bot.service /etc/systemd/system/"
ssh $SERVER_USER@$SERVER_IP "systemctl daemon-reload"
ssh $SERVER_USER@$SERVER_IP "systemctl enable telegram-bot"
success "Systemd сервис настроен"

# Создание скриптов управления
log "Создаем скрипты управления..."

# Скрипт обновления
ssh $BOT_USER@$SERVER_IP "cat > $PROJECT_DIR/update_bot.sh << 'EOF'
#!/bin/bash
cd $PROJECT_DIR
git pull origin main
cd bot
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart telegram-bot
echo \"Bot updated and restarted at \$(date)\"
EOF"

# Скрипт бэкапа
ssh $BOT_USER@$SERVER_IP "cat > $PROJECT_DIR/backup_bot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=\"$PROJECT_DIR/backups\"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

# Бэкап базы данных
if [ -f $PROJECT_DIR/bot/queue.db ]; then
    cp $PROJECT_DIR/bot/queue.db \$BACKUP_DIR/queue_\$DATE.db
fi

# Бэкап логов
if [ -f $PROJECT_DIR/bot/bot.log ]; then
    cp $PROJECT_DIR/bot/bot.log \$BACKUP_DIR/bot_\$DATE.log
fi

# Удаляем старые бэкапы (старше 7 дней)
find \$BACKUP_DIR -name \"*.db\" -mtime +7 -delete 2>/dev/null || true
find \$BACKUP_DIR -name \"*.log\" -mtime +7 -delete 2>/dev/null || true

echo \"Backup completed: \$DATE\"
EOF"

# Скрипт мониторинга
ssh $BOT_USER@$SERVER_IP "cat > $PROJECT_DIR/monitor_bot.sh << 'EOF'
#!/bin/bash
echo \"=== Telegram Bot Status ===\"
echo \"Service Status:\"
sudo systemctl status telegram-bot --no-pager -l
echo \"\nRecent Logs:\"
sudo journalctl -u telegram-bot --no-pager -n 20
echo \"\nDisk Usage:\"
df -h $PROJECT_DIR
echo \"\nMemory Usage:\"
free -h
EOF"

# Делаем скрипты исполняемыми
ssh $BOT_USER@$SERVER_IP "chmod +x $PROJECT_DIR/*.sh"
success "Скрипты управления созданы"

# Настройка cron для автоматического бэкапа
log "Настраиваем автоматический бэкап..."
ssh $BOT_USER@$SERVER_IP "crontab -l 2>/dev/null | grep -v backup_bot.sh | crontab -"
ssh $BOT_USER@$SERVER_IP "echo '0 2 * * * $PROJECT_DIR/backup_bot.sh' | crontab -"
success "Автоматический бэкап настроен"

# Настройка прав доступа
log "Настраиваем права доступа..."
ssh $SERVER_USER@$SERVER_IP "chown -R $BOT_USER:$BOT_USER $PROJECT_DIR"
ssh $SERVER_USER@$SERVER_IP "chmod 600 $PROJECT_DIR/bot/.env"
success "Права доступа настроены"

# Запуск бота
log "Запускаем бота..."
ssh $SERVER_USER@$SERVER_IP "systemctl start telegram-bot"
sleep 5

# Проверка статуса
log "Проверяем статус бота..."
if ssh $SERVER_USER@$SERVER_IP "systemctl is-active --quiet telegram-bot"; then
    success "Бот успешно запущен!"
else
    error "Ошибка запуска бота"
    log "Логи ошибок:"
    ssh $SERVER_USER@$SERVER_IP "journalctl -u telegram-bot --no-pager -n 20"
    exit 1
fi

# Финальная проверка
log "Выполняем финальную проверку..."
ssh $BOT_USER@$SERVER_IP "$PROJECT_DIR/monitor_bot.sh"

echo ""
success "🎉 Развертывание завершено успешно!"
echo ""
echo "📋 Полезные команды:"
echo "  Статус бота:     ./deploy/monitor_smart.sh"
echo "  Перезапуск:      ssh $SERVER_USER@$SERVER_IP 'systemctl restart telegram-bot'"
echo "  Обновление:      ssh $BOT_USER@$SERVER_IP '$PROJECT_DIR/update_bot.sh'"
echo "  Просмотр логов:  ssh $SERVER_USER@$SERVER_IP 'journalctl -u telegram-bot -f'"
echo "  Остановка:       ssh $SERVER_USER@$SERVER_IP 'systemctl stop telegram-bot'"
echo ""
echo "🔧 Файлы конфигурации:"
echo "  Сервис:          /etc/systemd/system/telegram-bot.service"
echo "  Конфиг:          $PROJECT_DIR/bot/.env"
echo "  Логи:            /var/log/telegram-bot/"
echo "  Бэкапы:          $PROJECT_DIR/backups/"
echo ""
echo "🚀 Ваш бот теперь работает круглосуточно!"

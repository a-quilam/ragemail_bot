#!/bin/bash

# Скрипт резервного копирования Telegram-бота
# Использование: ./backup.sh [server_ip] [local_backup_dir]

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

# Проверка параметров
if [ $# -lt 1 ]; then
    error "Использование: $0 <server_ip> [local_backup_dir]"
    error "Пример: $0 192.168.1.100 ./backups"
    exit 1
fi

SERVER_IP=$1
LOCAL_BACKUP_DIR=${2:-"./backups"}
SERVER_USER="root"
BOT_USER="botuser"
PROJECT_DIR="/home/$BOT_USER/ragemail_bot"
DATE=$(date +%Y%m%d_%H%M%S)

log "Создание резервной копии бота с сервера $SERVER_IP"

# Проверка подключения
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes $SERVER_USER@$SERVER_IP exit 2>/dev/null; then
    error "Не удается подключиться к серверу $SERVER_IP"
    exit 1
fi

# Создание локальной директории для бэкапа
mkdir -p "$LOCAL_BACKUP_DIR/$DATE"
log "Создана директория для бэкапа: $LOCAL_BACKUP_DIR/$DATE"

# Создание бэкапа на сервере
log "Создаем бэкап на сервере..."
ssh $BOT_USER@$SERVER_IP "$PROJECT_DIR/backup_bot.sh"

# Копирование файлов с сервера
log "Копируем файлы с сервера..."

# База данных
if ssh $BOT_USER@$SERVER_IP "test -f $PROJECT_DIR/bot/queue.db"; then
    log "Копируем базу данных..."
    scp $BOT_USER@$SERVER_IP:$PROJECT_DIR/bot/queue.db "$LOCAL_BACKUP_DIR/$DATE/queue.db"
    success "База данных скопирована"
else
    warning "База данных не найдена на сервере"
fi

# Логи
if ssh $BOT_USER@$SERVER_IP "test -f $PROJECT_DIR/bot/bot.log"; then
    log "Копируем логи..."
    scp $BOT_USER@$SERVER_IP:$PROJECT_DIR/bot/bot.log "$LOCAL_BACKUP_DIR/$DATE/bot.log"
    success "Логи скопированы"
else
    warning "Лог файл не найден на сервере"
fi

# Конфигурация
if ssh $BOT_USER@$SERVER_IP "test -f $PROJECT_DIR/bot/.env"; then
    log "Копируем конфигурацию..."
    scp $BOT_USER@$SERVER_IP:$PROJECT_DIR/bot/.env "$LOCAL_BACKUP_DIR/$DATE/.env"
    success "Конфигурация скопирована"
else
    warning "Файл конфигурации не найден на сервере"
fi

# Systemd сервис
log "Копируем конфигурацию сервиса..."
ssh $SERVER_USER@$SERVER_IP "cat /etc/systemd/system/telegram-bot.service" > "$LOCAL_BACKUP_DIR/$DATE/telegram-bot.service"
success "Конфигурация сервиса скопирована"

# Скрипты управления
log "Копируем скрипты управления..."
mkdir -p "$LOCAL_BACKUP_DIR/$DATE/scripts"
scp $BOT_USER@$SERVER_IP:$PROJECT_DIR/*.sh "$LOCAL_BACKUP_DIR/$DATE/scripts/" 2>/dev/null || warning "Скрипты не найдены"
success "Скрипты управления скопированы"

# Информация о системе
log "Собираем информацию о системе..."
{
    echo "=== ИНФОРМАЦИЯ О СИСТЕМЕ ==="
    echo "Дата создания бэкапа: $(date)"
    echo "Сервер: $SERVER_IP"
    echo ""
    echo "=== СТАТУС СЕРВИСА ==="
    ssh $SERVER_USER@$SERVER_IP "systemctl status telegram-bot --no-pager" 2>/dev/null || echo "Сервис недоступен"
    echo ""
    echo "=== ИСПОЛЬЗОВАНИЕ ДИСКА ==="
    ssh $SERVER_USER@$SERVER_IP "df -h" 2>/dev/null || echo "Информация недоступна"
    echo ""
    echo "=== ИСПОЛЬЗОВАНИЕ ПАМЯТИ ==="
    ssh $SERVER_USER@$SERVER_IP "free -h" 2>/dev/null || echo "Информация недоступна"
    echo ""
    echo "=== ПРОЦЕССЫ БОТА ==="
    ssh $SERVER_USER@$SERVER_IP "ps aux | grep 'python run_bot.py' | grep -v grep" 2>/dev/null || echo "Процессы не найдены"
    echo ""
    echo "=== ПОСЛЕДНИЕ ЛОГИ ==="
    ssh $SERVER_USER@$SERVER_IP "journalctl -u telegram-bot --no-pager -n 20" 2>/dev/null || echo "Логи недоступны"
} > "$LOCAL_BACKUP_DIR/$DATE/system_info.txt"
success "Информация о системе собрана"

# Создание архива
log "Создаем архив..."
cd "$LOCAL_BACKUP_DIR"
tar -czf "telegram-bot-backup-$DATE.tar.gz" "$DATE"
rm -rf "$DATE"
success "Архив создан: telegram-bot-backup-$DATE.tar.gz"

# Проверка размера архива
ARCHIVE_SIZE=$(du -h "telegram-bot-backup-$DATE.tar.gz" | cut -f1)
log "Размер архива: $ARCHIVE_SIZE"

# Очистка старых бэкапов (старше 30 дней)
log "Очищаем старые бэкапы..."
find "$LOCAL_BACKUP_DIR" -name "telegram-bot-backup-*.tar.gz" -mtime +30 -delete 2>/dev/null || true
OLD_BACKUPS=$(find "$LOCAL_BACKUP_DIR" -name "telegram-bot-backup-*.tar.gz" -mtime +30 2>/dev/null | wc -l)
if [ "$OLD_BACKUPS" -gt 0 ]; then
    success "Удалено $OLD_BACKUPS старых бэкапов"
else
    log "Старых бэкапов для удаления не найдено"
fi

# Список всех бэкапов
echo ""
log "Список всех бэкапов:"
ls -lh "$LOCAL_BACKUP_DIR"/telegram-bot-backup-*.tar.gz 2>/dev/null || echo "Бэкапы не найдены"

echo ""
success "🎉 Резервное копирование завершено успешно!"
echo ""
echo "📁 Архив сохранен: $LOCAL_BACKUP_DIR/telegram-bot-backup-$DATE.tar.gz"
echo "📊 Размер: $ARCHIVE_SIZE"
echo ""
echo "🔧 Для восстановления используйте:"
echo "  tar -xzf telegram-bot-backup-$DATE.tar.gz"
echo "  # Затем скопируйте файлы обратно на сервер"

#!/bin/bash

# Умный скрипт мониторинга Telegram-бота
# Автоматически читает IP сервера из config.sh

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

log "Мониторинг бота на сервере $SERVER_IP"

# Проверка подключения
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes $SERVER_USER@$SERVER_IP exit 2>/dev/null; then
    error "Не удается подключиться к серверу $SERVER_IP"
    error "Проверьте подключение к серверу"
    exit 1
fi

echo "=========================================="
echo "🤖 СТАТУС TELEGRAM-БОТА"
echo "=========================================="

# Статус сервиса
echo ""
log "Проверяем статус сервиса..."
SERVICE_STATUS=$(ssh $SERVER_USER@$SERVER_IP "systemctl is-active telegram-bot" 2>/dev/null || echo "inactive")

if [ "$SERVICE_STATUS" = "active" ]; then
    success "Сервис активен"
else
    error "Сервис неактивен"
fi

# Время работы
echo ""
log "Время работы сервиса..."
ACTIVE_TIME=$(ssh $SERVER_USER@$SERVER_IP "systemctl show telegram-bot --property=ActiveEnterTimestamp --value" 2>/dev/null || echo "Неизвестно")
echo "Запущен: $ACTIVE_TIME"

# Использование ресурсов
echo ""
log "Использование ресурсов..."
echo "CPU и память:"
BOT_PROCESS=$(ssh $SERVER_USER@$SERVER_IP "ps aux | grep 'python run_bot.py' | grep -v grep" 2>/dev/null || echo "Процесс не найден")
if [ "$BOT_PROCESS" != "Процесс не найден" ]; then
    echo "$BOT_PROCESS"
else
    warning "Процесс бота не найден"
fi

echo ""
echo "Использование диска:"
ssh $SERVER_USER@$SERVER_IP "df -h $PROJECT_DIR" 2>/dev/null || echo "Не удается получить информацию о диске"

echo ""
echo "Использование памяти:"
ssh $SERVER_USER@$SERVER_IP "free -h" 2>/dev/null || echo "Не удается получить информацию о памяти"

# Размер базы данных
echo ""
log "Размер базы данных..."
DB_SIZE=$(ssh $BOT_USER@$SERVER_IP "ls -lh $PROJECT_DIR/bot/queue.db 2>/dev/null | awk '{print \$5}'" || echo "Не найден")
if [ "$DB_SIZE" != "Не найден" ]; then
    echo "База данных: $DB_SIZE"
else
    warning "База данных не найдена"
fi

# Размер логов
echo ""
log "Размер логов..."
LOG_SIZE=$(ssh $BOT_USER@$SERVER_IP "ls -lh $PROJECT_DIR/bot/bot.log 2>/dev/null | awk '{print \$5}'" || echo "Не найден")
if [ "$LOG_SIZE" != "Не найден" ]; then
    echo "Лог файл: $LOG_SIZE"
else
    warning "Лог файл не найден"
fi

# Последние логи
echo ""
log "Последние 10 строк логов..."
ssh $SERVER_USER@$SERVER_IP "journalctl -u telegram-bot --no-pager -n 10" 2>/dev/null || echo "Логи недоступны"

# Проверка ошибок
echo ""
log "Проверяем наличие ошибок в логах..."
ERROR_COUNT=$(ssh $SERVER_USER@$SERVER_IP "journalctl -u telegram-bot --since '1 hour ago' --no-pager | grep -i error | wc -l" 2>/dev/null || echo "0")
if [ "$ERROR_COUNT" -gt 0 ]; then
    warning "Найдено $ERROR_COUNT ошибок за последний час"
    echo "Последние ошибки:"
    ssh $SERVER_USER@$SERVER_IP "journalctl -u telegram-bot --since '1 hour ago' --no-pager | grep -i error | tail -5" 2>/dev/null || echo "Ошибки недоступны"
else
    success "Ошибок за последний час не найдено"
fi

# Проверка сетевого подключения
echo ""
log "Проверяем сетевое подключение..."
if ssh $SERVER_USER@$SERVER_IP "curl -s --connect-timeout 5 https://api.telegram.org > /dev/null" 2>/dev/null; then
    success "Подключение к Telegram API доступно"
else
    error "Проблемы с подключением к Telegram API"
fi

# Проверка бэкапов
echo ""
log "Проверяем бэкапы..."
BACKUP_COUNT=$(ssh $BOT_USER@$SERVER_IP "ls -1 $PROJECT_DIR/backups/*.db 2>/dev/null | wc -l" || echo "0")
if [ "$BACKUP_COUNT" -gt 0 ]; then
    success "Найдено $BACKUP_COUNT бэкапов"
    echo "Последний бэкап:"
    ssh $BOT_USER@$SERVER_IP "ls -lt $PROJECT_DIR/backups/*.db 2>/dev/null | head -1" || echo "Информация недоступна"
else
    warning "Бэкапы не найдены"
fi

# Проверка cron задач
echo ""
log "Проверяем cron задачи..."
CRON_JOBS=$(ssh $BOT_USER@$SERVER_IP "crontab -l 2>/dev/null | grep -v '^#' | wc -l" || echo "0")
if [ "$CRON_JOBS" -gt 0 ]; then
    success "Найдено $CRON_JOBS cron задач"
    echo "Активные задачи:"
    ssh $BOT_USER@$SERVER_IP "crontab -l 2>/dev/null | grep -v '^#'" || echo "Задачи недоступны"
else
    warning "Cron задачи не настроены"
fi

echo ""
echo "=========================================="
echo "📊 СВОДКА"
echo "=========================================="

if [ "$SERVICE_STATUS" = "active" ]; then
    success "Бот работает нормально"
else
    error "Бот не работает"
fi

if [ "$ERROR_COUNT" -eq 0 ]; then
    success "Ошибок не обнаружено"
else
    warning "Обнаружены ошибки в логах"
fi

echo ""
echo "🔧 Полезные команды:"
echo "  Перезапуск:      ssh $SERVER_USER@$SERVER_IP 'systemctl restart telegram-bot'"
echo "  Просмотр логов:  ssh $SERVER_USER@$SERVER_IP 'journalctl -u telegram-bot -f'"
echo "  Обновление:      ssh $BOT_USER@$SERVER_IP '$PROJECT_DIR/update_bot.sh'"
echo "  Бэкап:           ssh $BOT_USER@$SERVER_IP '$PROJECT_DIR/backup_bot.sh'"

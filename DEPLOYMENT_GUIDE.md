# 🚀 Руководство по развертыванию Telegram-бота на сервере

## Обзор

Это руководство поможет вам развернуть вашего Telegram-бота на сервере для круглосуточной работы. Мы рассмотрим несколько вариантов: от простого VPS до облачных решений.

## 📋 Варианты серверов

### 1. VPS (Virtual Private Server) - Рекомендуется
**Провайдеры:**
- **Timeweb** (Россия) - от 200₽/месяц
- **Beget** (Россия) - от 150₽/месяц  
- **DigitalOcean** - от $4/месяц
- **Vultr** - от $2.5/месяц
- **Hetzner** - от €3/месяц

**Минимальные требования:**
- 1 CPU ядро
- 512MB RAM
- 10GB SSD
- Ubuntu 20.04+ или Debian 11+

### 2. Облачные платформы
- **Heroku** (бесплатный план убран, от $7/месяц)
- **Railway** - от $5/месяц
- **Render** - от $7/месяц

## 🛠 Пошаговая инструкция для VPS

### Шаг 1: Подготовка сервера

1. **Подключитесь к серверу:**
```bash
ssh root@your-server-ip
```

2. **Обновите систему:**
```bash
apt update && apt upgrade -y
```

3. **Установите необходимые пакеты:**
```bash
apt install -y python3 python3-pip python3-venv git nginx supervisor
```

### Шаг 2: Настройка пользователя

1. **Создайте пользователя для бота:**
```bash
adduser botuser
usermod -aG sudo botuser
```

2. **Переключитесь на пользователя:**
```bash
su - botuser
```

### Шаг 3: Клонирование и настройка проекта

1. **Клонируйте репозиторий:**
```bash
cd /home/botuser
git clone https://github.com/your-username/ragemail_bot.git
cd ragemail_bot
```

2. **Создайте виртуальное окружение:**
```bash
cd bot
python3 -m venv venv
source venv/bin/activate
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка переменных окружения

1. **Создайте файл .env:**
```bash
nano .env
```

2. **Добавьте необходимые переменные:**
```env
# Telegram Bot Token
BOT_TOKEN=your_bot_token_here

# База данных
DB_PATH=/home/botuser/ragemail_bot/bot/queue.db

# Логирование
LOG_LEVEL=INFO

# Часовой пояс
TIMEZONE=Europe/Moscow

# Сетевые настройки
NETWORK_MONITOR_INTERVAL=30
```

### Шаг 5: Создание systemd сервиса

1. **Создайте файл сервиса:**
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

2. **Добавьте конфигурацию:**
```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/ragemail_bot/bot
Environment=PATH=/home/botuser/ragemail_bot/bot/venv/bin
ExecStart=/home/botuser/ragemail_bot/bot/venv/bin/python run_bot.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

# Безопасность
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/botuser/ragemail_bot/bot

[Install]
WantedBy=multi-user.target
```

3. **Активируйте сервис:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### Шаг 6: Мониторинг и управление

1. **Проверьте статус:**
```bash
sudo systemctl status telegram-bot
```

2. **Просмотр логов:**
```bash
sudo journalctl -u telegram-bot -f
```

3. **Перезапуск бота:**
```bash
sudo systemctl restart telegram-bot
```

4. **Остановка бота:**
```bash
sudo systemctl stop telegram-bot
```

## 🔧 Дополнительные настройки

### Автоматическое обновление

1. **Создайте скрипт обновления:**
```bash
nano /home/botuser/update_bot.sh
```

2. **Добавьте содержимое:**
```bash
#!/bin/bash
cd /home/botuser/ragemail_bot
git pull origin main
cd bot
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart telegram-bot
echo "Bot updated and restarted"
```

3. **Сделайте исполняемым:**
```bash
chmod +x /home/botuser/update_bot.sh
```

### Резервное копирование

1. **Создайте скрипт бэкапа:**
```bash
nano /home/botuser/backup_bot.sh
```

2. **Добавьте содержимое:**
```bash
#!/bin/bash
BACKUP_DIR="/home/botuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап базы данных
cp /home/botuser/ragemail_bot/bot/queue.db $BACKUP_DIR/queue_$DATE.db

# Бэкап логов
cp /home/botuser/ragemail_bot/bot/bot.log $BACKUP_DIR/bot_$DATE.log

# Удаляем старые бэкапы (старше 7 дней)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.log" -mtime +7 -delete

echo "Backup completed: $DATE"
```

3. **Настройте cron для автоматического бэкапа:**
```bash
crontab -e
```

4. **Добавьте строку для ежедневного бэкапа в 2:00:**
```bash
0 2 * * * /home/botuser/backup_bot.sh
```

## 🌐 Развертывание на облачных платформах

### Heroku

1. **Установите Heroku CLI**
2. **Создайте Procfile:**
```
worker: cd bot && python run_bot.py
```

3. **Создайте runtime.txt:**
```
python-3.11.0
```

4. **Добавьте переменные окружения в Heroku Dashboard**

5. **Деплой:**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### Railway

1. **Подключите GitHub репозиторий**
2. **Настройте переменные окружения**
3. **Укажите команду запуска:**
```
cd bot && python run_bot.py
```

## 📊 Мониторинг и логирование

### Настройка логирования

1. **Создайте директорию для логов:**
```bash
mkdir -p /var/log/telegram-bot
chown botuser:botuser /var/log/telegram-bot
```

2. **Обновите systemd сервис для записи в файл:**
```ini
StandardOutput=append:/var/log/telegram-bot/bot.log
StandardError=append:/var/log/telegram-bot/bot-error.log
```

### Мониторинг через Telegram

Добавьте в бота команду для мониторинга статуса:

```python
@router.message(Command("status"))
async def cmd_status(message: Message):
    # Проверка статуса системы
    status = "🟢 Бот работает нормально"
    await message.answer(status)
```

## 🔒 Безопасность

### Основные меры безопасности:

1. **Настройте firewall:**
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

2. **Используйте SSH ключи вместо паролей**

3. **Регулярно обновляйте систему:**
```bash
sudo apt update && sudo apt upgrade -y
```

4. **Ограничьте доступ к файлам бота:**
```bash
chmod 600 /home/botuser/ragemail_bot/bot/.env
chmod 755 /home/botuser/ragemail_bot/bot
```

## 🚨 Устранение неполадок

### Частые проблемы:

1. **Бот не запускается:**
```bash
sudo journalctl -u telegram-bot --no-pager
```

2. **Ошибки с базой данных:**
```bash
# Проверьте права доступа
ls -la /home/botuser/ragemail_bot/bot/queue.db
```

3. **Проблемы с сетью:**
```bash
# Проверьте подключение к Telegram API
curl -s https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe
```

4. **Нехватка памяти:**
```bash
# Добавьте swap файл
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 📈 Масштабирование

### Для высоких нагрузок:

1. **Используйте более мощный сервер**
2. **Настройте load balancer**
3. **Используйте Redis для кэширования**
4. **Настройте мониторинг (Prometheus + Grafana)**

## 💰 Примерные расходы

- **VPS (Timeweb)**: 200-500₽/месяц
- **VPS (DigitalOcean)**: $4-10/месяц
- **Heroku**: $7-25/месяц
- **Railway**: $5-20/месяц

## 📞 Поддержка

Если у вас возникли проблемы:

1. Проверьте логи: `sudo journalctl -u telegram-bot -f`
2. Убедитесь, что все переменные окружения настроены
3. Проверьте права доступа к файлам
4. Убедитесь, что сервер имеет доступ к интернету

---

**Удачи с развертыванием! 🚀**

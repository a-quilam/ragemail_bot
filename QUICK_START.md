# 🚀 Быстрый старт: Развертывание Telegram-бота на сервере

## Что вам нужно

1. **VPS сервер** (рекомендуемые провайдеры):
   - Timeweb (Россия) - от 200₽/месяц
   - Beget (Россия) - от 150₽/месяц
   - DigitalOcean - от $4/месяц
   - Vultr - от $2.5/месяц

2. **Токен бота** от @BotFather в Telegram

3. **SSH доступ** к серверу

## ⚡ Автоматическое развертывание (5 минут)

### Шаг 1: Подготовка
```bash
# Скачайте проект
git clone https://github.com/your-username/ragemail_bot.git
cd ragemail_bot

# Сделайте скрипты исполняемыми
chmod +x deploy/*.sh
```

### Шаг 2: Развертывание
```bash
# Запустите автоматическое развертывание
./deploy/deploy.sh YOUR_SERVER_IP YOUR_BOT_TOKEN
```

**Пример:**
```bash
./deploy/deploy.sh 192.168.1.100 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Шаг 3: Проверка
```bash
# Проверьте статус бота
./deploy/monitor.sh YOUR_SERVER_IP
```

## 🎉 Готово!

Ваш бот теперь работает круглосуточно! 

## 📋 Полезные команды

```bash
# Мониторинг
./deploy/monitor.sh YOUR_SERVER_IP

# Резервное копирование
./deploy/backup.sh YOUR_SERVER_IP

# Перезапуск бота
ssh root@YOUR_SERVER_IP 'systemctl restart telegram-bot'

# Просмотр логов
ssh root@YOUR_SERVER_IP 'journalctl -u telegram-bot -f'
```

## 🔧 Ручное развертывание

Если автоматический скрипт не работает, следуйте [подробному руководству](DEPLOYMENT_GUIDE.md).

## 💰 Примерные расходы

- **VPS (Timeweb)**: 200-500₽/месяц
- **VPS (DigitalOcean)**: $4-10/месяц
- **Heroku**: $7-25/месяц

## 🆘 Помощь

Если что-то не работает:
1. Проверьте логи: `ssh root@YOUR_SERVER_IP 'journalctl -u telegram-bot --no-pager'`
2. Убедитесь, что токен бота правильный
3. Проверьте подключение к интернету на сервере

---

**Удачи! 🚀**

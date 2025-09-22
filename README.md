# 📧 RageMail Bot - Анонимный Telegram-бот

> Профессиональный Telegram-бот для анонимной переписки с продвинутой архитектурой

> ⚠️ **ВНИМАНИЕ: Это бета-версия (v0.1.1b). Функциональность может быть нестабильной.**

> 🚨 **КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ: Этот бот полностью написан вайб-кодом!** 
> 
> Используйте на свой страх и риск. Тру-пограммисты должны лезть в код только в средствах индивидуальной защиты. 
> Бот всё ещё может работать, но стабильность не гарантируется.

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.1b-orange.svg)](CHANGELOG.md)
[![Beta](https://img.shields.io/badge/Status-Beta-red.svg)](CHANGELOG.md)
[![GitHub release](https://img.shields.io/github/release/a-quilam/ragemail_bot.svg)](https://github.com/a-quilam/ragemail_bot/releases)

## 🚀 Быстрый старт

1. **Создайте .env файл:**
   ```bash
   cp bot/.env.example bot/.env
   # Отредактируйте bot/.env и добавьте BOT_TOKEN
   ```

2. **Установите зависимости:**
   ```bash
   pip install -r bot/requirements.txt
   ```

3. **Запустите бота:**
   ```bash
   cd bot && python -m app.main
   ```

## ✨ Особенности

- 🔒 **Анонимная переписка** через каналы
- 🛡️ **Продвинутая система безопасности** с валидацией
- ⚡ **Высокая производительность** с оптимизированной архитектурой
- 🔄 **Отказоустойчивость** с circuit breakers и rollback системой
- 📊 **Мониторинг** и логирование всех операций
- 🎯 **Профессиональная архитектура** с разделением ответственности

> 💀 **ВАЙБ-КОД ПРЕДУПРЕЖДЕНИЕ:** Вот это я навалил вайб-кода! 
> 
> Код написан в состоянии творческого вдохновения и может содержать неожиданные решения. 
> Используйте с осторожностью и не удивляйтесь странным комментариям в коде.

## 🏗️ Архитектура

### 📁 Структура проекта
```
bot/
├── app/
│   ├── core/           # Конфигурация и константы
│   ├── features/       # Основная логика бота
│   ├── infra/          # База данных и API
│   ├── services/       # Бизнес-логика
│   ├── utils/          # Утилиты и валидация
│   └── validators/     # Валидация данных
├── tests/              # Тесты
└── docs/               # Документация
```

### 🔧 Ключевые компоненты
- **Circuit Breaker** - защита от сбоев
- **Concurrency Manager** - управление конкурентностью
- **Performance Logger** - мониторинг производительности
- **Rollback Manager** - откат изменений при ошибках
- **Resource Manager** - управление ресурсами

### Порядок роутеров (КРИТИЧЕСКИ ВАЖНО!)
Порядок включения роутеров в `main.py` имеет критическое значение:

```python
dp.include_router(admin_router)      # 1. Админские функции - ПЕРВЫЙ!
dp.include_router(start_router)      # 2. Команды /start, /help, /cancel
dp.include_router(bind_router)       # 3. Обработка start payload
dp.include_router(write_router)      # 4. Написание писем - ДОЛЖЕН БЫТЬ ПЕРЕД relay_router!
dp.include_router(relay_router)      # 5. /end команда и релеи
dp.include_router(channel_router)    # 6. Callback кнопки каналов
dp.include_router(auto_detect_router) # 7. Автоматическое обнаружение каналов
dp.include_router(debug_router)      # 8. Отладочный роутер - последний
dp.include_router(direct_write_router) # 9. Прямое написание для обычных пользователей
```

**ВАЖНО:** `write_router` должен быть ПЕРЕД `relay_router`, иначе обработчик `pipe` в `relay_router` будет перехватывать все текстовые сообщения.

### Компоненты системы написания писем

#### 1. Write Router (`app/features/write/router.py`)

**Назначение:** Основной роутер для обработки написания писем

**Обработчики:**
- `on_write_button` - обработка кнопки "✍️ Написать письмо"
- `on_text_input` - обработка текста в состоянии `INPUT_TEXT`
- `on_auto_text_input` - автоматическая обработка текста для обычных пользователей
- TTL обработчики - выбор времени жизни поста
- Callback обработчики - отправка, отмена, удаление черновиков

**Фильтры:**
```python
# Кнопка написания письма
router.message.register(on_write_button, F.text == "✍️ Написать письмо")

# Обработка текста в состоянии INPUT_TEXT
router.message.register(on_text_input, StateFilter(WriteStates.INPUT_TEXT))

# Автоматическая обработка текста (с кастомным фильтром)
router.message.register(on_auto_text_input, auto_text_filter)
```

**Кастомный фильтр `auto_text_filter`:**
```python
async def auto_text_filter(message, state: FSMContext):
    # Исключаем кнопки
    if message.text and any(message.text.startswith(prefix) for prefix in ["✍️", "⚙️", "📊", "📌", "🔄", "🛡️"]):
        return False
    
    # Исключаем состояние INPUT_TEXT (обрабатывается on_text_input)
    current_state = await state.get_state()
    if current_state == WriteStates.INPUT_TEXT:
        return False
    
    return True
```

#### 2. Write Button Handler (`app/features/write/action_write_button.py`)

**Назначение:** Обработка нажатия кнопки "✍️ Написать письмо"

**Функция:** `on_write_button(m, state, active_mailbox_id, **kwargs)`

**Что делает:**
1. Очищает состояние постпина (если пользователь в нем находится)
2. Устанавливает FSM состояние в `WriteStates.INPUT_TEXT`
3. Отправляет приглашение для ввода текста
4. Показывает клавиатуру с подсказками

#### 3. Text Input Handler (`app/features/write/state_input_text.py`)

**Назначение:** Обработка текста, введенного пользователем в состоянии `INPUT_TEXT`

**Функция:** `on_text_input(m, state, db, tz, active_mailbox_id)`

**Что делает:**
1. Валидирует текст (длина, пустота)
2. Генерирует псевдоним для пользователя
3. Сохраняет текст в FSM данные
4. Переводит в состояние `WriteStates.CHOOSE_TTL`
5. Показывает клавиатуру выбора времени жизни поста

#### 4. Auto Text Handler (`app/features/write/auto_text_handler.py`)

**Назначение:** Автоматическая обработка текста для обычных пользователей (не админов)

**Функция:** `on_auto_text_input(m, state, db, active_mailbox_id, tz)`

**Что делает:**
1. Проверяет, что пользователь не админ
2. Если админ в состоянии `INPUT_TEXT` - НЕ перехватывает сообщение
3. Для обычных пользователей - автоматически начинает процесс написания письма

#### 5. Relay Router (`app/features/relay/router.py`)

**Назначение:** Обработка команд релея и перехват сообщений для релея

**Обработчики:**
- `cmd_end` - команда `/end`
- `pipe` - перехват сообщений для релея

**ВАЖНО:** `pipe` обработчик имеет фильтр, который исключает кнопки:
```python
router.message.register(pipe, ~F.text.startswith("✍️") & ~F.text.startswith("⚙️") & ...)
```

#### 6. Direct Write Router (`app/main.py`)

**Назначение:** Прямое написание писем обычными пользователями без кнопок

**Фильтр:** `not_in_fsm_filter` - пропускает только сообщения от пользователей НЕ в FSM состоянии

### FSM Состояния (`app/fsm/write_states.py`)

```python
class WriteStates(StatesGroup):
    INPUT_TEXT = State()      # Пользователь вводит текст письма
    CHOOSE_TTL = State()      # Пользователь выбирает время жизни поста
    PREVIEW = State()         # Предварительный просмотр письма
```

### Поток выполнения

#### Для админов (с кнопкой):
1. Пользователь нажимает "✍️ Написать письмо"
2. `on_write_button` устанавливает состояние `INPUT_TEXT`
3. Пользователь вводит текст
4. `on_text_input` обрабатывает текст, переводит в `CHOOSE_TTL`
5. Пользователь выбирает время жизни
6. Письмо публикуется

#### Для обычных пользователей (без кнопки):
1. Пользователь просто пишет текст
2. `on_auto_text_input` автоматически начинает процесс
3. Далее как у админов

### Критические моменты

#### 1. Порядок роутеров
- `write_router` ДОЛЖЕН быть ПЕРЕД `relay_router`
- Иначе `pipe` в `relay_router` перехватит все сообщения

#### 2. Фильтры
- `auto_text_filter` исключает состояние `INPUT_TEXT`
- `pipe` исключает кнопки
- `not_in_fsm_filter` исключает FSM состояния

#### 3. Обработка админов
- Админы используют кнопки
- `on_auto_text_input` НЕ перехватывает сообщения админов в состоянии `INPUT_TEXT`

### Отладка

Если кнопка "✍️ Написать письмо" не работает:

1. **Проверьте порядок роутеров** - `write_router` должен быть ПЕРЕД `relay_router`
2. **Проверьте фильтры** - убедитесь, что нет конфликтующих фильтров
3. **Проверьте логи** - ищите сообщения от обработчиков
4. **Проверьте FSM состояния** - убедитесь, что состояния устанавливаются правильно

### Файлы системы

```
app/features/write/
├── router.py              # Основной роутер
├── action_write_button.py # Обработка кнопки
├── state_input_text.py    # Обработка текста
├── auto_text_handler.py   # Автоматическая обработка
├── ttl_handlers.py        # Обработка TTL
└── action_*.py           # Другие действия

app/fsm/
└── write_states.py        # FSM состояния

app/main.py                # Порядок роутеров
```

## 🛠️ Технологии

- **Python 3.13+** - основной язык
- **aiogram 3.x** - Telegram Bot API
- **aiosqlite** - асинхронная база данных
- **asyncio** - асинхронное программирование
- **Pydantic** - валидация данных

## 📊 Статистика проекта

- **138 Python файлов**
- **~16,400 строк кода**
- **9 основных модулей**
- **Полное покрытие тестами**

## 🚀 Развертывание

### Локальная разработка
```bash
# Клонируйте репозиторий
git clone https://github.com/a-quilam/ragemail_bot.git
cd ragemail_bot

# Установите зависимости
pip install -r bot/requirements.txt

# Настройте .env файл
cp bot/.env.example bot/.env
# Добавьте BOT_TOKEN в bot/.env

# Запустите бота
cd bot && python -m app.main
```

### Docker (опционально)
```bash
# Создайте Dockerfile в корне проекта
# Запустите через Docker
docker build -t ragemail-bot .
docker run -d ragemail-bot
```

## 🤝 Вклад в проект

1. **Fork** репозитория
2. **Создайте** feature branch (`git checkout -b feature/amazing-feature`)
3. **Сделайте** коммит (`git commit -m 'Add amazing feature'`)
4. **Отправьте** в branch (`git push origin feature/amazing-feature`)
5. **Откройте** Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 👨‍💻 Автор

**a-quilam** - [GitHub](https://github.com/a-quilam)

## 🙏 Благодарности

- Команде aiogram за отличную библиотеку
- Сообществу Python за поддержку
- Всем контрибьюторам проекта

---

⭐ **Если проект вам понравился, поставьте звезду!**
## Git Setup Complete! 🎉

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def start_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[],  # Пустая клавиатура - пользователи сразу пишут сообщения
        resize_keyboard=True,
        selective=True,
        input_field_placeholder="Напишите ваше анонимное сообщение...",
    )


def start_kb_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✍️ Написать письмо")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📌 Закрепить пост"), KeyboardButton(text="🔄 Обновить")],
            [KeyboardButton(text="🛡️ Антиспам")]
        ],
        resize_keyboard=True,
        selective=True,
        input_field_placeholder="Факт → как это на тебя повлияло → чего ты просишь сейчас.",
    )

def ttl_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="15 минут"),
                KeyboardButton(text="1 час"),
                KeyboardButton(text="6 часов")
            ],
            [
                KeyboardButton(text="12 часов"),
                KeyboardButton(text="Сутки")
            ],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        selective=True,
        input_field_placeholder="Выберите время жизни поста...",
    )

def back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад")]],
        resize_keyboard=True,
        selective=True,
        input_field_placeholder="Нажмите кнопку для возврата...",
    )


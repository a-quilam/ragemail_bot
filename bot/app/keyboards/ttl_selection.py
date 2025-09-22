from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from zoneinfo import ZoneInfo
from app.core.timefmt import fmt_expiry

def ttl_selection_kb(current_ttl_seconds: int, max_ttl_seconds: int, tz: ZoneInfo) -> InlineKeyboardMarkup:
    # Кнопки TTL в секундах
    ttl_buttons = [
        (900, "+15 мин"),    # 15 минут
        (1800, "+30 мин"),   # 30 минут
        (3600, "+1 ч"),      # 1 час
        (21600, "+6 ч"),     # 6 часов
        (43200, "+12 ч"),    # 12 часов
        (86400, "+24 ч"),    # 24 часа
    ]
    
    # Создаём кнопки с текущим TTL
    buttons = []
    for ttl_sec, label in ttl_buttons:
        total_ttl = current_ttl_seconds + ttl_sec
        if total_ttl <= max_ttl_seconds:
            buttons.append(InlineKeyboardButton(
                text=f"{label} ({fmt_expiry(total_ttl, tz)})",
                callback_data=f"ttl_add:{ttl_sec}"
            ))
    
    # Показываем ожидаемое сгорание только когда остается 2 кнопки или меньше
    if len(buttons) > 2:
        # Убираем ожидаемое сгорание для всех кнопок
        buttons = []
        for ttl_sec, label in ttl_buttons:
            total_ttl = current_ttl_seconds + ttl_sec
            if total_ttl <= max_ttl_seconds:
                buttons.append(InlineKeyboardButton(
                    text=label,
                    callback_data=f"ttl_add:{ttl_sec}"
                ))
    
    # Раскладываем: 3 в первом ряду, до 3 во втором (ожидаемо +6 +12 +24 в одном ряду)
    keyboard = []
    row1 = buttons[:3]
    row2 = buttons[3:6]
    if row1:
        keyboard.append(row1)
    if row2:
        keyboard.append(row2)
    
    # Добавляем кнопки управления
    keyboard.append([
        InlineKeyboardButton(text="✅ Готово", callback_data="ttl_done"),
        InlineKeyboardButton(text="🔄 Сбросить", callback_data="ttl_reset")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

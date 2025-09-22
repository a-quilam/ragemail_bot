from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def preview_kb(draft_id: int, allow_delay: bool = True) -> InlineKeyboardMarkup:
    # First row: Send and Delete buttons
    btns = [
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data=f"send_now:{draft_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_draft:{draft_id}")
        ]
    ]
    # Second row: Delayed send button (if allowed)
    if allow_delay:
        btns.append([InlineKeyboardButton(text="⏳ Отправить через 2 минуты", callback_data=f"send_delay:{draft_id}")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def delayed_cancel_kb(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Не отправлять. Удалить", callback_data=f"cancel_delay:{item_id}")
    ]])

def confirmation_kb(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения для критических действий"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, подтверждаю", callback_data=f"confirm:{action}:{item_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel:{action}:{item_id}")
    ]])

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def settings_kb(is_superadmin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="➕ Создать почтовый ящик"), KeyboardButton(text="📦 Управление ящиками")]
    ]
    if is_superadmin:
        rows.append([KeyboardButton(text="👤 Добавить админа"), KeyboardButton(text="🗑️ Удалить админа")])
    rows.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        selective=True,
        input_field_placeholder="Выберите действие из меню...",
    )

def confirm_box_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="box:confirm")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="box:back")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="box:cancel")],
    ])

def mailbox_management_kb(mailboxes, active_mailbox_id, user_id: int = None, is_superadmin: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для управления ящиками"""
    buttons = []
    
    for mailbox_id, title, _, _, _, creator_id in mailboxes:
        row = []
        
        # Кнопка для установки активного ящика
        if mailbox_id != active_mailbox_id:
            row.append(InlineKeyboardButton(
                text=f"✅ {title}",
                callback_data=f"set_active:{mailbox_id}"
            ))
        else:
            row.append(InlineKeyboardButton(
                text=f"⚪ {title} (активный)",
                callback_data=f"set_active:{mailbox_id}"
            ))
        
        # Кнопка для настройки кнопок (для создателя ящика или суперадмина)
        if user_id and (creator_id == user_id or is_superadmin):
            row.append(InlineKeyboardButton(
                text="🔧",
                callback_data=f"button_config:{mailbox_id}"
            ))
        
        # Кнопка для передачи прав на ящик (только для создателя ящика)
        if user_id and creator_id == user_id:
            row.append(InlineKeyboardButton(
                text="🔄",
                callback_data=f"transfer_admin:{mailbox_id}"
            ))
        
        # Кнопка для удаления ящика
        row.append(InlineKeyboardButton(
            text="🗑️",
            callback_data=f"delete_mailbox:{mailbox_id}"
        ))
        
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

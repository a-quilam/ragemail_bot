from aiogram import types
from aiogram.fsm.context import FSMContext
from app.fsm.admin_states import ButtonConfigStates
from app.infra.repo.button_configs_repo import ButtonConfigsRepo
from app.utils.mailbox_permissions import can_manage_mailbox

async def cb_button_config_start(c: types.CallbackQuery, state: FSMContext, db):
    """Начать настройку кнопок"""
    if not c.data.startswith("button_config:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, c.from_user.id, mailbox_id):
        await c.answer("❌ У вас нет прав для настройки кнопок этого ящика.", show_alert=True)
        return
    
    # Сохраняем ID ящика в состоянии
    await state.set_data({"mailbox_id": mailbox_id})
    await state.set_state(ButtonConfigStates.MAIN)
    
    await show_button_config_menu(c, db, mailbox_id)
    await c.answer()

async def show_button_config_menu_new(m: types.Message, db, mailbox_id: int):
    """Показать меню настройки кнопок через новое сообщение"""
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    text = "🔧 <b>Настройка кнопок под постами</b>\n\n"
    text += "Доступные кнопки:\n"
    text += "[+15m] - кнопка \"+15 мин\"\n"
    text += "[+30m] - кнопка \"+30 мин\"\n"
    text += "[+1h] - кнопка \"+1 ч\"\n"
    text += "[+2h] - кнопка \"+2 ч\"\n"
    text += "[+3h] - кнопка \"+3 ч\"\n"
    text += "[+6h] - кнопка \"+6 ч\"\n"
    text += "[+12h] - кнопка \"+12 ч\"\n"
    text += "[+24h] - кнопка \"+24 ч\"\n"
    text += "[speak] - кнопка \"💬 Поговорить\"\n\n"
    
    # Показываем текущую конфигурацию
    text += "Актуальная конфигурация:\n"
    if config:
        config_lines = []
        for row in config:
            if row.get("type") == "row":
                row_buttons = row.get("buttons", [])
                if row_buttons:
                    button_tags = []
                    for button in row_buttons:
                        if button.get("type") == "extend":
                            if "15m" in button.get("callback_data", ""):
                                button_tags.append("[+15m]")
                            elif "30m" in button.get("callback_data", ""):
                                button_tags.append("[+30m]")
                            elif "1h" in button.get("callback_data", ""):
                                button_tags.append("[+1h]")
                            elif "2h" in button.get("callback_data", ""):
                                button_tags.append("[+2h]")
                            elif "3h" in button.get("callback_data", ""):
                                button_tags.append("[+3h]")
                            elif "6h" in button.get("callback_data", ""):
                                button_tags.append("[+6h]")
                            elif "12h" in button.get("callback_data", ""):
                                button_tags.append("[+12h]")
                            elif "24h" in button.get("callback_data", ""):
                                button_tags.append("[+24h]")
                        elif button.get("type") == "contact":
                            button_tags.append("[speak]")
                        elif button.get("type") == "custom":
                            button_tags.append(f"[{button['text']}]")
                    if button_tags:
                        config_lines.append(" ".join(button_tags))
        
        if config_lines:
            text += "\n".join(config_lines)
        else:
            text += "Нет активных кнопок"
    else:
        text += "[+1h] [speak]"
    
    text += "\n\nОтправьте новую конфигурацию кнопок.\n"
    text += "Кнопки в квадратных скобках через пробел.\n"
    text += "Пример:\n"
    text += "[+1h] [speak]"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔄 Сбросить к умолчанию", callback_data=f"reset_buttons:{mailbox_id}")]
    ])
    
    await m.answer(text, reply_markup=keyboard, parse_mode="HTML")

async def show_button_config_menu(c: types.CallbackQuery, db, mailbox_id: int):
    """Показать меню настройки кнопок"""
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    text = "🔧 <b>Настройка кнопок под постами</b>\n\n"
    text += "Доступные кнопки:\n"
    text += "[+15m] - кнопка \"+15 мин\"\n"
    text += "[+30m] - кнопка \"+30 мин\"\n"
    text += "[+1h] - кнопка \"+1 ч\"\n"
    text += "[+2h] - кнопка \"+2 ч\"\n"
    text += "[+3h] - кнопка \"+3 ч\"\n"
    text += "[+6h] - кнопка \"+6 ч\"\n"
    text += "[+12h] - кнопка \"+12 ч\"\n"
    text += "[+24h] - кнопка \"+24 ч\"\n"
    text += "[speak] - кнопка \"💬 Поговорить\"\n\n"
    
    # Показываем текущую конфигурацию
    text += "Актуальная конфигурация:\n"
    if config:
        config_lines = []
        for row in config:
            if row.get("type") == "row":
                row_buttons = row.get("buttons", [])
                if row_buttons:
                    button_tags = []
                    for button in row_buttons:
                        if button.get("type") == "extend":
                            if "15m" in button.get("callback_data", ""):
                                button_tags.append("[+15m]")
                            elif "30m" in button.get("callback_data", ""):
                                button_tags.append("[+30m]")
                            elif "1h" in button.get("callback_data", ""):
                                button_tags.append("[+1h]")
                            elif "2h" in button.get("callback_data", ""):
                                button_tags.append("[+2h]")
                            elif "3h" in button.get("callback_data", ""):
                                button_tags.append("[+3h]")
                            elif "6h" in button.get("callback_data", ""):
                                button_tags.append("[+6h]")
                            elif "12h" in button.get("callback_data", ""):
                                button_tags.append("[+12h]")
                            elif "24h" in button.get("callback_data", ""):
                                button_tags.append("[+24h]")
                        elif button.get("type") == "contact":
                            button_tags.append("[speak]")
                        elif button.get("type") == "custom":
                            button_tags.append(f"[{button['text']}]")
                    if button_tags:
                        config_lines.append(" ".join(button_tags))
        
        if config_lines:
            text += "\n".join(config_lines)
        else:
            text += "Нет активных кнопок"
    else:
        text += "[+1h] [speak]"
    
    text += "\n\nОтправьте новую конфигурацию кнопок.\n"
    text += "Кнопки в квадратных скобках через пробел.\n"
    text += "Пример:\n"
    text += "[+1h] [speak]"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔄 Сбросить к умолчанию", callback_data=f"reset_buttons:{mailbox_id}")]
    ])
    
    await c.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await c.answer()

async def on_button_config_text(m: types.Message, state: FSMContext, db):
    """Обработать текстовую конфигурацию кнопок"""
    data = await state.get_data()
    mailbox_id = data.get("mailbox_id")
    
    if not mailbox_id:
        await m.answer("Ошибка: не найден ID ящика.")
        await state.clear()
        return
    
    # Парсим конфигурацию с сохранением структуры строк
    import re
    new_config = []
    
    print(f"DEBUG: Parsing config from text: {repr(m.text)}")
    
    # Разбиваем на строки
    lines = m.text.strip().split('\n')
    print(f"DEBUG: Lines: {lines}")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Ищем все кнопки в строке
        button_pattern = r'\[([^\]]+)\]'
        matches = re.findall(button_pattern, line)
        
        if not matches:
            continue
            
        print(f"DEBUG: Line '{line}' has buttons: {matches}")
        
        # Создаем строку кнопок
        row_buttons = []
        for tag in matches:
            tag = tag.strip()  # Убираем пробелы
            print(f"DEBUG: Processing tag: {repr(tag)}")
            
            if tag == "+15m":
                row_buttons.append({
                    "type": "extend",
                    "text": "+15 мин",
                    "callback_data": "ext:15m",
                    "enabled": True
                })
            elif tag == "+30m":
                row_buttons.append({
                    "type": "extend",
                    "text": "+30 мин",
                    "callback_data": "ext:30m",
                    "enabled": True
                })
            elif tag == "+1h":
                row_buttons.append({
                    "type": "extend",
                    "text": "+1 ч",
                    "callback_data": "ext:1h",
                    "enabled": True
                })
            elif tag == "+2h":
                row_buttons.append({
                    "type": "extend",
                    "text": "+2 ч",
                    "callback_data": "ext:2h",
                    "enabled": True
                })
            elif tag == "+3h":
                row_buttons.append({
                    "type": "extend",
                    "text": "+3 ч",
                    "callback_data": "ext:3h",
                    "enabled": True
                })
            elif tag == "+6h":
                row_buttons.append({
                    "type": "extend",
                    "text": "+6 ч",
                    "callback_data": "ext:6h",
                    "enabled": True
                })
            elif tag == "+12h":
                row_buttons.append({
                    "type": "extend",
                    "text": "+12 ч",
                    "callback_data": "ext:12h",
                    "enabled": True
                })
            elif tag == "+24h":
                row_buttons.append({
                    "type": "extend",
                    "text": "+24 ч",
                    "callback_data": "ext:24h",
                    "enabled": True
                })
            elif tag == "speak":
                row_buttons.append({
                    "type": "contact",
                    "text": "💬 Поговорить",
                    "callback_data": "contact",
                    "enabled": True
                })
            else:
                # Кастомная кнопка
                row_buttons.append({
                    "type": "custom",
                    "text": tag,
                    "callback_data": f"custom:{len(tag)}",
                    "enabled": True
                })
        
        # Добавляем строку кнопок в конфигурацию
        if row_buttons:
            new_config.append({
                "type": "row",
                "buttons": row_buttons
            })
    
    print(f"DEBUG: Final config: {new_config}")
    
    # Сохраняем конфигурацию
    config_repo = ButtonConfigsRepo(db)
    await config_repo.set_config(mailbox_id, new_config)
    
    await state.clear()
    await m.answer("✅ Конфигурация кнопок обновлена!")
    
    # Показываем обновленное меню через новое сообщение
    await show_button_config_menu_new(m, db, mailbox_id)

async def cb_add_button(c: types.CallbackQuery, state: FSMContext, db):
    """Добавить новую кнопку"""
    if not c.data.startswith("add_button:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    await state.set_state(ButtonConfigStates.ADD_BUTTON)
    
    text = "➕ <b>Добавление новой кнопки</b>\n\n"
    text += "Отправьте текст кнопки. Например:\n"
    text += "• \"👍 Нравится\"\n"
    text += "• \"📝 Комментарий\"\n"
    text += "• \"🔗 Поделиться\"\n\n"
    text += "После добавления кнопки вы сможете настроить её действие."
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"button_config:{mailbox_id}")]
    ])
    
    await c.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await c.answer()

async def on_add_button_text(m: types.Message, state: FSMContext, db):
    """Обработать текст новой кнопки"""
    data = await state.get_data()
    mailbox_id = data.get("mailbox_id")
    
    if not mailbox_id:
        await m.answer("Ошибка: не найден ID ящика.")
        await state.clear()
        return
    
    button_text = m.text.strip()
    
    # Создаем новую кнопку
    new_button = {
        "type": "custom",
        "text": button_text,
        "callback_data": f"custom:{len(button_text)}",  # Простой callback_data
        "enabled": True
    }
    
    # Добавляем кнопку в конфигурацию
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    # Если конфигурация пустая или не содержит строк, создаем новую строку
    if not config or not any(row.get("type") == "row" for row in config):
        config = [{"type": "row", "buttons": []}]
    
    # Добавляем кнопку в первую строку
    if config[0].get("type") == "row":
        config[0]["buttons"].append(new_button)
    else:
        # Если структура неправильная, создаем новую
        config = [{"type": "row", "buttons": [new_button]}]
    
    await config_repo.set_config(mailbox_id, config)
    
    await state.clear()
    await m.answer(f"✅ Кнопка \"{button_text}\" добавлена!")
    
    # Показываем обновленное меню
    from aiogram.types import CallbackQuery
    fake_callback = CallbackQuery(
        id="fake",
        from_user=m.from_user,
        chat_instance="fake",
        message=m,
        data=f"button_config:{mailbox_id}"
    )
    await show_button_config_menu(fake_callback, db, mailbox_id)

async def cb_edit_button(c: types.CallbackQuery, state: FSMContext, db):
    """Редактировать кнопки"""
    if not c.data.startswith("edit_button:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    # Собираем все кнопки из всех строк
    all_buttons = []
    for row in config:
        if row.get("type") == "row":
            all_buttons.extend(row.get("buttons", []))
    
    if not all_buttons:
        await c.answer("❌ Нет кнопок для редактирования.", show_alert=True)
        return
    
    text = "✏️ <b>Редактирование кнопок</b>\n\n"
    text += "Выберите кнопку для редактирования:\n\n"
    
    keyboard_buttons = []
    for i, button in enumerate(all_buttons):
        status = "✅" if button.get("enabled", True) else "❌"
        text += f"{i+1}. {status} {button['text']}\n"
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=f"{i+1}. {button['text']}", 
                callback_data=f"edit_button_item:{mailbox_id}:{i}"
            )
        ])
    
    keyboard_buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"button_config:{mailbox_id}")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await c.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await c.answer()

async def cb_edit_button_item(c: types.CallbackQuery, state: FSMContext, db):
    """Редактировать конкретную кнопку"""
    if not c.data.startswith("edit_button_item:"):
        return
    
    parts = c.data.split(":")
    mailbox_id = int(parts[1])
    button_index = int(parts[2])
    
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    # Собираем все кнопки из всех строк
    all_buttons = []
    for row in config:
        if row.get("type") == "row":
            all_buttons.extend(row.get("buttons", []))
    
    if button_index >= len(all_buttons):
        await c.answer("❌ Кнопка не найдена.", show_alert=True)
        return
    
    button = all_buttons[button_index]
    
    text = f"✏️ <b>Редактирование кнопки</b>\n\n"
    text += f"Текст: {button['text']}\n"
    text += f"Статус: {'Включена' if button.get('enabled', True) else 'Отключена'}\n\n"
    text += "Выберите действие:"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="🔄 Включить" if not button.get('enabled', True) else "⏸️ Отключить",
                callback_data=f"toggle_button:{mailbox_id}:{button_index}"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"delete_button:{mailbox_id}:{button_index}"
            )
        ],
        [
            types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_button:{mailbox_id}")
        ]
    ])
    
    await c.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await c.answer()

async def cb_toggle_button(c: types.CallbackQuery, state: FSMContext, db):
    """Переключить состояние кнопки"""
    if not c.data.startswith("toggle_button:"):
        return
    
    parts = c.data.split(":")
    mailbox_id = int(parts[1])
    button_index = int(parts[2])
    
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    # Находим кнопку в структуре
    current_index = 0
    button_found = False
    for row in config:
        if row.get("type") == "row":
            buttons = row.get("buttons", [])
            if button_index < current_index + len(buttons):
                # Кнопка найдена в этой строке
                local_index = button_index - current_index
                buttons[local_index]["enabled"] = not buttons[local_index].get("enabled", True)
                button_found = True
                break
            current_index += len(buttons)
    
    if not button_found:
        await c.answer("❌ Кнопка не найдена.", show_alert=True)
        return
    
    await config_repo.set_config(mailbox_id, config)
    await c.answer("✅ Состояние кнопки изменено!")
    
    # Обновляем интерфейс
    await cb_edit_button_item(c, state, db)

async def cb_delete_button(c: types.CallbackQuery, state: FSMContext, db):
    """Удалить кнопку"""
    if not c.data.startswith("delete_button:"):
        return
    
    parts = c.data.split(":")
    mailbox_id = int(parts[1])
    button_index = int(parts[2])
    
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    # Находим кнопку в структуре
    current_index = 0
    button_found = False
    button = None
    for row in config:
        if row.get("type") == "row":
            buttons = row.get("buttons", [])
            if button_index < current_index + len(buttons):
                # Кнопка найдена в этой строке
                local_index = button_index - current_index
                button = buttons[local_index]
                button_found = True
                break
            current_index += len(buttons)
    
    if not button_found or not button:
        await c.answer("❌ Кнопка не найдена.", show_alert=True)
        return
    
    text = f"🗑️ <b>Удаление кнопки</b>\n\n"
    text += f"Вы уверены, что хотите удалить кнопку \"{button['text']}\"?\n\n"
    text += "Это действие нельзя отменить."
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="✅ Да, удалить",
                callback_data=f"confirm_delete_button:{mailbox_id}:{button_index}"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"edit_button_item:{mailbox_id}:{button_index}"
            )
        ]
    ])
    
    await c.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await c.answer()

async def cb_confirm_delete_button(c: types.CallbackQuery, state: FSMContext, db):
    """Подтвердить удаление кнопки"""
    if not c.data.startswith("confirm_delete_button:"):
        return
    
    parts = c.data.split(":")
    mailbox_id = int(parts[1])
    button_index = int(parts[2])
    
    config_repo = ButtonConfigsRepo(db)
    config = await config_repo.get_config(mailbox_id)
    
    # Находим и удаляем кнопку в структуре
    current_index = 0
    button_found = False
    deleted_button = None
    for row in config:
        if row.get("type") == "row":
            buttons = row.get("buttons", [])
            if button_index < current_index + len(buttons):
                # Кнопка найдена в этой строке
                local_index = button_index - current_index
                deleted_button = buttons.pop(local_index)
                button_found = True
                break
            current_index += len(buttons)
    
    if not button_found or not deleted_button:
        await c.answer("❌ Кнопка не найдена.", show_alert=True)
        return
    
    await config_repo.set_config(mailbox_id, config)
    await c.answer(f"✅ Кнопка \"{deleted_button['text']}\" удалена!")
    
    # Возвращаемся к редактированию
    await cb_edit_button(c, state, db)

async def cb_reset_buttons(c: types.CallbackQuery, state: FSMContext, db):
    """Сбросить кнопки к умолчанию"""
    if not c.data.startswith("reset_buttons:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    
    text = "🔄 <b>Сброс кнопок</b>\n\n"
    text += "Вы уверены, что хотите сбросить все кнопки к настройкам по умолчанию?\n\n"
    text += "Это действие нельзя отменить."
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="✅ Да, сбросить",
                callback_data=f"confirm_reset_buttons:{mailbox_id}"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"button_config:{mailbox_id}"
            )
        ]
    ])
    
    await c.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await c.answer()

async def cb_confirm_reset_buttons(c: types.CallbackQuery, state: FSMContext, db):
    """Подтвердить сброс кнопок"""
    if not c.data.startswith("confirm_reset_buttons:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    
    # Сбрасываем к настройкам по умолчанию
    config_repo = ButtonConfigsRepo(db)
    await config_repo.delete_config(mailbox_id)  # Удаляем кастомную конфигурацию
    
    await c.answer("✅ Кнопки сброшены к настройкам по умолчанию!")
    
    # Показываем обновленное меню
    await show_button_config_menu(c, db, mailbox_id)

import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from app.fsm.admin_states import CreateBoxStates
from app.keyboards.write_flow import back_kb
from app.keyboards.settings import confirm_box_kb

async def cb_create_box(m: types.Message, state: FSMContext, db):
    """Начало создания почтового ящика"""
    logging.info(f"CREATE BOX: Starting mailbox creation for user {m.from_user.id}")
    
    try:
        # Очищаем состояние только если оно не пустое (избегаем потери данных при ошибках)
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
        
        # Используем простую реализацию добавления канала
        from .simple_channel_add import cb_add_channel_simple
        await cb_add_channel_simple(m, state, db)
        
    except Exception as e:
        logging.error(f"Error in cb_create_box: {e}")
        await m.answer(f"❌ Ошибка при запуске создания ящика: {str(e)}")

async def cb_select_channel(callback: types.CallbackQuery, state: FSMContext, db):
    """Обработчик выбора канала"""
    logging.info(f"SELECT CHANNEL: User {callback.from_user.id} selected channel")
    
    try:
        # Валидируем и извлекаем ID канала из callback_data
        if not callback.data or ":" not in callback.data:
            await callback.answer("❌ Неверные данные канала", show_alert=True)
            return
            
        parts = callback.data.split(":")
        if len(parts) != 2 or not parts[1].lstrip('-').isdigit():
            await callback.answer("❌ Неверный формат ID канала", show_alert=True)
            return
            
        channel_id = int(parts[1])
        
        # Получаем информацию о канале
        try:
            chat = await callback.bot.get_chat(channel_id)
            channel_name = chat.title or f"Канал {channel_id}"
        except TelegramAPIError as e:
            await callback.answer(f"❌ Не удалось получить информацию о канале: {e}", show_alert=True)
            return
        
        # Сохраняем данные
        await state.update_data(
            name=channel_name,
            channel_id=channel_id
        )
        await state.set_state(CreateBoxStates.CONFIRM)
        
        # Показываем подтверждение
        summary = (
            "📦 Создание почтового ящика\n\n"
            f"Название: {channel_name}\n"
            f"Канал: {channel_id}\n\n"
            "Подтвердить создание?"
        )
        
        await callback.message.edit_text(summary, reply_markup=confirm_box_kb())
        await callback.answer()
        
    except ValueError as e:
        logging.error(f"Invalid channel ID format: {e}")
        await callback.answer("❌ Неверный формат ID канала", show_alert=True)
    except Exception as e:
        logging.error(f"Error selecting channel: {e}")
        await callback.answer(f"❌ Ошибка при выборе канала: {str(e)}", show_alert=True)

async def cb_refresh_channel_list(callback: types.CallbackQuery, state: FSMContext, db):
    """Обработчик обновления списка каналов"""
    logging.info(f"REFRESH CHANNEL LIST: User {callback.from_user.id} wants to refresh channel list")
    
    try:
        from app.services.channel_tracker import ChannelTracker
        tracker = ChannelTracker(db)
        available_channels = await tracker.get_user_available_channels(callback.bot, callback.from_user.id)
        
        if not available_channels:
            await callback.message.edit_text(
                "❌ Не найдено доступных каналов.\n\n"
                "Возможно, бот был удален из каналов или потерял права администратора.\n\n"
                "Добавьте бота в канал как администратора и нажмите 'Обновить список' снова."
            )
            await callback.answer()
            return
        
        # Показываем доступные каналы
        text = "📦 <b>Выберите канал для создания почтового ящика</b>\n\n"
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard_buttons = []
        
        for channel in available_channels:
            status_icon = "📦" if channel.get("existing") else "📺"
            text += f"{status_icon} {channel['title']}\n"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{status_icon} {channel['title']}", 
                    callback_data=f"select_channel:{channel['id']}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="🔄 Обновить список", 
                callback_data="refresh_channel_list"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error refreshing channel list: {e}")
        await callback.message.edit_text(f"Ошибка при обновлении списка каналов: {e}")
        await callback.answer()



async def cb_cancel_box(callback: types.CallbackQuery, state: FSMContext, db):
    """Обработчик отмены создания ящика"""
    logging.info(f"CANCEL BOX: User {callback.from_user.id} cancelled box creation")
    
    await state.clear()
    await callback.message.edit_text("❌ Создание почтового ящика отменено.")
    await callback.answer()

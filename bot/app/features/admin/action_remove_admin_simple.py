"""
Упрощенная версия удаления администратора
Аналогично action_add_admin.py - простая и эффективная
"""
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
import logging
from app.fsm.admin_states import RemoveAdminStates
from app.infra.repo.users_repo import UsersRepo
from app.keyboards.common import confirmation_kb
from app.utils.admin_logger import log_remove_admin
from app.utils.fsm_utils import safe_clear_state, handle_fsm_error, ensure_state_cleared_on_exit

async def on_remove_admin_start(m: types.Message, state: FSMContext, db):
    await state.set_state(RemoveAdminStates.ASK_USER)
    
    # Получаем список текущих администраторов
    try:
        users_repo = UsersRepo(db)
        admins = await users_repo.get_admins()
        
        text = "👥 <b>Удаление администратора</b>\n\n"
        text += "Текущие администраторы:\n\n"
        
        for user_id, role in admins:
            try:
                chat = await m.bot.get_chat(user_id)
                username = chat.username if chat.username else None
                first_name = chat.first_name or ""
                last_name = chat.last_name or ""
                full_name = f"{first_name} {last_name}".strip()
                
                if username:
                    display_name = f"<code>@{username}</code>"
                elif full_name:
                    display_name = full_name
                else:
                    display_name = f"ID {user_id}"
                    
                text += f"👤 {display_name} — {role}\n"
            except TelegramAPIError:
                text += f"🆔 <code>{user_id}</code> — {role}\n"
        
        text += "\nДля удаления администратора отправьте его user_id цифрами, @username или перешлите его сообщение."
        
    except Exception as e:
        logging.error(f"Error getting admins list: {e}")
        text = "👥 <b>Удаление администратора</b>\n\nОтправьте user_id цифрами, @username или перешлите сообщение пользователя."
    
    await m.answer(text, parse_mode="HTML")

async def on_remove_admin_input(m: types.Message, state: FSMContext, db):
    logging.info(f"REMOVE ADMIN INPUT: user {m.from_user.id}, text: '{m.text}', state: {await state.get_state()}")
    
    # Проверяем, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != RemoveAdminStates.ASK_USER:
        logging.warning(f"REMOVE ADMIN INPUT: Wrong state {current_state}, expected {RemoveAdminStates.ASK_USER}")
        await safe_clear_state(state, m.from_user.id)
        return
    
    # Проверка на наличие текста
    if not m.text and not m.forward_from:
        logging.warning(f"REMOVE ADMIN INPUT: No text or forward message from user {m.from_user.id}")
        await m.answer("❌ Пожалуйста, отправьте user_id цифрами, @username или перешлите сообщение пользователя.")
        await safe_clear_state(state, m.from_user.id)
        return

    try:
        target_user_id = None
        username = None

        # Пересланное сообщение
        if m.forward_from:
            target_user_id = m.forward_from.id
        # Числовой ID
        elif m.text and m.text.strip().isdigit():
            target_user_id = int(m.text.strip())
        # @username → сначала пробуем через get_chat, потом ищем в базе данных
        elif m.text and m.text.strip().startswith('@'):
            username = m.text.strip()[1:]  # убираем @
            
            # Сначала пробуем найти в базе данных
            users_repo = UsersRepo(db)
            target_user_id = await users_repo.get_by_username(username)
            
            if not target_user_id:
                # Если не найден в базе, пробуем через get_chat
                try:
                    chat = await m.bot.get_chat(f"@{username}")
                    if chat and hasattr(chat, 'id') and chat.id:
                        target_user_id = chat.id
                    else:
                        await m.answer("Не удалось получить ID пользователя по @username. Пришлите числовой ID или пересланное сообщение.")
                        await safe_clear_state(state, m.from_user.id)
                        return
                except TelegramAPIError:
                    await m.answer(
                        f"❌ <b>Не удалось найти пользователя</b>\n\n"
                        f"@username не найден или пользователь не существует.\n"
                        f"Для удаления администратора используйте:\n"
                        f"• Числовой ID (например: 123456789)\n"
                        f"• Пересланное сообщение от пользователя\n"
                        f"• @username (если пользователь уже взаимодействовал с ботом)",
                        parse_mode="HTML"
                    )
                    await safe_clear_state(state, m.from_user.id)
                    return

        if not target_user_id:
            logging.warning(f"REMOVE ADMIN INPUT: Could not determine user_id from input: text='{m.text}', forward_from={m.forward_from}")
            await m.answer("❌ Не смог определить пользователя. Пришлите user_id цифрами или перешлите его сообщение.")
            await safe_clear_state(state, m.from_user.id)
            return

        # Проверяем, что пользователь является администратором
        users_repo = UsersRepo(db)
        current_role = await users_repo.get_role(target_user_id)
        if current_role != "admin":
            await m.answer(f"❌ Пользователь {target_user_id} не является администратором.")
            await safe_clear_state(state, m.from_user.id)
            return

        # Запрашиваем подтверждение
        display_name = f"@{username}" if username else f"<code>{target_user_id}</code>"
        confirmation_text = (
            f"⚠️ <b>Подтверждение удаления администратора</b>\n\n"
            f"Вы действительно хотите удалить права администратора у пользователя {display_name}?\n\n"
            f"<i>Это действие нельзя отменить!</i>"
        )
        
        await m.answer(
            confirmation_text,
            parse_mode="HTML",
            reply_markup=confirmation_kb("remove_admin", target_user_id)
        )
        
        # Сохраняем данные в состоянии
        await state.update_data(target_user_id=target_user_id, username=username)
        await state.set_state(RemoveAdminStates.CONFIRM)
        
    except Exception as e:
        logging.error(f"REMOVE ADMIN ERROR: Unexpected error for user {m.from_user.id}: {e}")
        await handle_fsm_error(m, state, "❌ Произошла неожиданная ошибка при обработке запроса.")

async def on_remove_admin_confirm(callback: types.CallbackQuery, state: FSMContext, db):
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        username = data.get('username')
        
        if not target_user_id:
            await callback.answer("❌ Ошибка: не найден ID пользователя.", show_alert=True)
            await state.clear()
            return
        
        # Удаляем роль админа (возвращаем к user)
        users_repo = UsersRepo(db)
        await users_repo.upsert(target_user_id, role="user")
        logging.info(f"Successfully removed admin role from user {target_user_id} by admin {callback.from_user.id}")
        
        # Логируем действие
        log_remove_admin(callback.from_user.id, target_user_id, username)
        
        await state.clear()
        
        # Формируем отображаемое имя пользователя
        display_name = f"@{username}" if username else f"<code>{target_user_id}</code>"
        
        await callback.message.edit_text(
            f"✅ <b>Администратор удален</b>\n\n"
            f"Пользователь {display_name} больше не администратор.",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"REMOVE ADMIN CONFIRM ERROR: Failed to remove admin role: {e}")
        await callback.answer("❌ Ошибка при удалении прав администратора.", show_alert=True)
        await state.clear()

async def on_remove_admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Удаление администратора отменено.")
    await callback.answer()
    await state.clear()

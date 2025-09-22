from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
import logging
from app.fsm.admin_states import AddAdminStates
from app.infra.repo.users_repo import UsersRepo
from app.utils.admin_logger import log_add_admin
from app.utils.fsm_utils import safe_clear_state, handle_fsm_error, ensure_state_cleared_on_exit

async def on_add_admin_start(m: types.Message, state: FSMContext):
    await state.set_state(AddAdminStates.ASK_USER)
    await m.answer("Отправьте user_id пользователя цифрами, @username или перешлите его сообщение сюда.")

async def on_add_admin_input(m: types.Message, state: FSMContext, db):
    import logging
    logging.info(f"ADD ADMIN INPUT: user {m.from_user.id}, text: '{m.text}', state: {await state.get_state()}")
    
    # Проверяем, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != AddAdminStates.ASK_USER:
        logging.warning(f"ADD ADMIN INPUT: Wrong state {current_state}, expected {AddAdminStates.ASK_USER}")
        await safe_clear_state(state, m.from_user.id)
        return
    
    # Дополнительная проверка на наличие текста
    if not m.text and not m.forward_from:
        logging.warning(f"ADD ADMIN INPUT: No text or forward message from user {m.from_user.id}")
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
                        # Сохраняем username в базе для будущих поисков
                        await users_repo.update_username(target_user_id, username)
                    else:
                        await m.answer("Не удалось получить ID пользователя по @username. Пришлите числовой ID или пересланное сообщение.")
                        await safe_clear_state(state, m.from_user.id)
                        return
                except TelegramAPIError:
                    await m.answer(
                        f"❌ <b>Не удалось найти пользователя</b>\n\n"
                        f"@username не найден или пользователь не существует.\n"
                        f"Для добавления администратора используйте:\n"
                        f"• Числовой ID (например: 123456789)\n"
                        f"• Пересланное сообщение от пользователя\n"
                        f"• @username (если пользователь уже взаимодействовал с ботом)",
                        parse_mode="HTML"
                    )
                    await safe_clear_state(state, m.from_user.id)
                    return

        if not target_user_id:
            logging.warning(f"ADD ADMIN INPUT: Could not determine user_id from input: text='{m.text}', forward_from={m.forward_from}")
            await m.answer("❌ Не смог определить пользователя. Пришлите user_id цифрами или перешлите его сообщение.")
            await safe_clear_state(state, m.from_user.id)
            return

        # Назначаем роль админа
        try:
            await UsersRepo(db).upsert(target_user_id, role="admin", username=username)
            
            # Уведомляем трекер событий
            try:
                from app.utils.role_change_tracker import get_role_change_tracker
                tracker = get_role_change_tracker()
                await tracker.on_admin_added(target_user_id, username)
            except Exception as e:
                logging.warning(f"Failed to notify role tracker: {e}")
            logging.info(f"ADD ADMIN SUCCESS: User {target_user_id} added as admin by {m.from_user.id}")
        except Exception as e:
            logging.error(f"ADD ADMIN ERROR: Failed to add user {target_user_id} as admin: {e}")
            await m.answer("❌ Произошла ошибка при добавлении администратора. Попробуйте еще раз.")
            await safe_clear_state(state, m.from_user.id)
            return
        
        # Логируем действие
        log_add_admin(m.from_user.id, target_user_id, username)
        
        await ensure_state_cleared_on_exit(
            state, 
            m.from_user.id,
            f"✅ Пользователь {target_user_id} назначен администратором.",
            m
        )
        
        # Уведомляем нового администратора и обновляем его интерфейс
        try:
            from app.keyboards.write_flow import start_kb_admin
            await m.bot.send_message(
                target_user_id,
                "🎉 <b>Поздравляем!</b>\n\n"
                "Вы назначены администратором бота «Злое письмо».\n\n"
                "Теперь у вас есть доступ к панели управления:\n"
                "✍️ <b>Написать письмо</b> — создать анонимное сообщение\n"
                "⚙️ <b>Настройки</b> — управление ящиками и пользователями\n"
                "📊 <b>Статистика</b> — просмотр статистики\n"
                "📌 <b>Закрепить пост</b> — создать deeplink-пост\n"
                "🔄 <b>Обновить</b> — синхронизация с каналом",
                reply_markup=start_kb_admin()
            )
        except TelegramAPIError:
            pass  # Пользователь может заблокировать бота
            
    except Exception as e:
        logging.error(f"ADD ADMIN ERROR: Unexpected error for user {m.from_user.id}: {e}")
        await handle_fsm_error(m, state, "❌ Произошла неожиданная ошибка при добавлении администратора.")
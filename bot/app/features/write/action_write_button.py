from aiogram import types
from aiogram.fsm.context import FSMContext
from app.fsm.write_states import WriteStates
from app.texts.prompts import PROMPT_INPUT
from typing import Optional
import logging

async def on_write_button(m: types.Message, state: FSMContext, active_mailbox_id: Optional[int] = None, **kwargs):
    # Очищаем состояние постпина, если пользователь в нем находится
    from app.features.admin.cmd_postpin import clear_postpin_wait
    clear_postpin_wait(m.from_user.id)
    
    # Игнорируем неожиданные параметры от middleware без логирования
    # Это нормальное поведение - middleware передает дополнительные параметры
    # которые не используются в данном обработчике
    
    logging.info(f"WRITE BUTTON CLICKED by user {m.from_user.id}, active_mailbox_id: {active_mailbox_id}, text: '{m.text}'")
    logging.info(f"WRITE BUTTON: Current FSM state: {await state.get_state()}")
    
    if m.text == "✍️ Написать письмо":
        # ПРОВЕРЯЕМ ПРАВА ДОСТУПА - кнопка только для админов
        from app.infra.repo.users_repo import UsersRepo
        from app.core.config import settings
        
        # Получаем роль пользователя из middleware или проверяем вручную
        db = kwargs.get('db')
        if not db:
            logging.error(f"No database connection available for user {m.from_user.id}")
            await m.answer("❌ Ошибка доступа к базе данных. Попробуйте позже.")
            return
        
        users_repo = UsersRepo(db)
        role = await users_repo.get_role(m.from_user.id)
        is_admin = role in ("admin", "superadmin") or (settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID)
        
        if not is_admin:
            logging.warning(f"Non-admin user {m.from_user.id} tried to access write button")
            await m.answer(
                "❌ <b>Доступ ограничен</b>\n\n"
                "Эта функция доступна только администраторам.\n\n"
                "Для отправки анонимных сообщений просто напишите текст напрямую.",
                parse_mode="HTML"
            )
            return
        logging.info(f"WRITE BUTTON: Processing write button for user {m.from_user.id}, active_mailbox_id: {active_mailbox_id}")
        # Проверяем, не в процессе ли уже написания письма
        try:
            current_state = await state.get_state()
            if current_state == WriteStates.INPUT_TEXT:
                await m.answer("📝 Вы уже в процессе написания письма")
                return
        except Exception as e:
            logging.error(f"Error getting FSM state: {e}")
            # Продолжаем выполнение, так как это не критическая ошибка
        
        if not active_mailbox_id:
            logging.info(f"No active mailbox for user {m.from_user.id}")
            await m.answer(
                "❌ У вас не настроен активный почтовый ящик.\n\n"
                "Для написания писем необходимо:\n"
                "1. Создать почтовый ящик в настройках\n"
                "2. Или привязаться к существующему ящику\n\n"
                "Перейдите в ⚙️ Настройки для настройки ящика."
            )
            return
        
        logging.info(f"Setting state to INPUT_TEXT for user {m.from_user.id}")
        # Очищаем состояние, но сохраняем данные AntispamStates если они есть
        current_state = await state.get_state()
        if current_state and str(current_state).startswith("AntispamStates"):
            # Сохраняем данные антиспама перед очисткой
            antispam_data = await state.get_data()
            await state.clear()
            await state.set_state(WriteStates.INPUT_TEXT)
            # Восстанавливаем данные антиспама
            await state.update_data(antispam_data)
            logging.info(f"Preserved AntispamStates data when switching to WriteStates for user {m.from_user.id}")
        else:
            await state.clear()
            await state.set_state(WriteStates.INPUT_TEXT)
        # Remove keyboard
        await m.answer(PROMPT_INPUT, reply_markup=types.ReplyKeyboardRemove())
        logging.info(f"Write button response sent to user {m.from_user.id}")

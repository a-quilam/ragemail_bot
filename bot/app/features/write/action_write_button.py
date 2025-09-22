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
    
    # Валидация kwargs для предотвращения неожиданных параметров
    if kwargs:
        logging.warning(f"Unexpected kwargs in on_write_button: {list(kwargs.keys())}")
        # Очищаем kwargs для безопасности
        kwargs.clear()
    
    logging.info(f"WRITE BUTTON CLICKED by user {m.from_user.id}, active_mailbox_id: {active_mailbox_id}, text: '{m.text}'")
    logging.info(f"WRITE BUTTON: Current FSM state: {await state.get_state()}")
    
    if m.text == "✍️ Написать письмо":
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
        await state.clear()
        await state.set_state(WriteStates.INPUT_TEXT)
        # Remove keyboard
        await m.answer(PROMPT_INPUT, reply_markup=types.ReplyKeyboardRemove())
        logging.info(f"Write button response sent to user {m.from_user.id}")

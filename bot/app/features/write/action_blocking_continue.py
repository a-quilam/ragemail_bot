"""
Обработчик кнопки "Хорошо, не буду нарушать" после блокировки сообщения
"""
import logging
from aiogram import types
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

async def on_blocking_continue(m: types.Message, state: FSMContext, db):
    """
    Обработчик кнопки "Хорошо, не буду нарушать" после блокировки сообщения
    
    Args:
        m: Message объект
        state: FSM контекст
        db: База данных
    """
    try:
        # КРИТИЧНО: Защита от повторных нажатий
        # Между нажатием кнопки и редактированием сообщения есть временной промежуток
        data = await state.get_data()
        if data.get('blocking_button_pressed'):
            logger.info(f"User {m.from_user.id} tried to press blocking button again, ignoring")
            return
        
        # Отмечаем, что кнопка была нажата (защита от повторных нажатий)
        await state.update_data(blocking_button_pressed=True)
        
        # КРИТИЧНО: Принудительно убираем ReplyKeyboard
        # one_time_keyboard=True НЕ РАБОТАЕТ надежно в Telegram Bot API
        from aiogram.types import ReplyKeyboardRemove
        
        # Отправляем дружелюбное сообщение с ПРИНУДИТЕЛЬНЫМ удалением клавиатуры
        await m.answer(
            "✅ <b>Спасибо!</b>\n\n"
            "Теперь можете написать новое письмо.\n\n",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Очищаем ID из FSM состояния (больше не нужен)
        await state.update_data(blocking_message_id=None)
        
        # КРИТИЧНО: Гарантируем правильное состояние
        from app.fsm.write_states import WriteStates
        current_state = await state.get_state()
        if current_state != WriteStates.INPUT_TEXT:
            await state.set_state(WriteStates.INPUT_TEXT)
        
        logger.info(f"User {m.from_user.id} acknowledged blocking and continued work")
        
    except Exception as e:
        logger.error(f"Error in on_blocking_continue: {e}")
        await m.answer("❌ Произошла ошибка. Попробуйте еще раз.")

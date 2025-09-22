"""
Middleware для автоматической очистки FSM состояний при ошибках
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

class FSMCleanupMiddleware(BaseMiddleware):
    """
    Middleware для автоматической очистки FSM состояний при ошибках
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события с автоматической очисткой состояний при ошибках
        """
        try:
            # Выполняем обработчик
            return await handler(event, data)
        except Exception as e:
            # Логируем ошибку
            logger.error(f"Error in handler: {e}", exc_info=True)
            
            # Пытаемся очистить FSM состояние, но НЕ очищаем AntispamStates
            try:
                state: FSMContext = data.get("state")
                if state:
                    current_state = await state.get_state()
                    if current_state and not str(current_state).startswith("AntispamStates"):
                        logger.info(f"Clearing FSM state {current_state} due to error")
                        await state.clear()
                    elif current_state and str(current_state).startswith("AntispamStates"):
                        logger.info(f"Preserving AntispamStates {current_state} despite error")
            except Exception as cleanup_error:
                logger.error(f"Failed to clear FSM state: {cleanup_error}")
            
            # Отправляем сообщение об ошибке пользователю
            try:
                if isinstance(event, Message):
                    await event.answer(
                        "❌ <b>Произошла ошибка</b>\n\n"
                        "Попробуйте еще раз или обратитесь к администратору.",
                        parse_mode="HTML"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ Произошла ошибка. Попробуйте еще раз.",
                        show_alert=True
                    )
            except Exception as message_error:
                logger.error(f"Failed to send error message: {message_error}")
            
            # Пробрасываем ошибку дальше
            raise

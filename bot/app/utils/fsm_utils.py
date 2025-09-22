"""
Утилиты для работы с FSM состояниями
"""
import logging
from typing import Optional, Any
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

async def safe_clear_state(state: FSMContext, user_id: Optional[int] = None) -> bool:
    """
    Безопасная очистка FSM состояния с логированием
    
    Args:
        state: FSM контекст
        user_id: ID пользователя для логирования (опционально)
    
    Returns:
        bool: True если состояние было очищено успешно
    """
    try:
        current_state = await state.get_state()
        if current_state:
            await state.clear()
            if user_id:
                logger.info(f"FSM state cleared for user {user_id}: {current_state}")
            else:
                logger.info(f"FSM state cleared: {current_state}")
            return True
        return False
    except Exception as e:
        if user_id:
            logger.error(f"Failed to clear FSM state for user {user_id}: {e}")
        else:
            logger.error(f"Failed to clear FSM state: {e}")
        return False

async def handle_fsm_error(
    event: Message | CallbackQuery, 
    state: FSMContext, 
    error_message: str = "❌ Произошла ошибка. Состояние сброшено.",
    clear_state: bool = True
) -> None:
    """
    Обработка ошибок в FSM с автоматической очисткой состояния
    
    Args:
        event: Событие (Message или CallbackQuery)
        state: FSM контекст
        error_message: Сообщение об ошибке для пользователя
        clear_state: Очищать ли состояние при ошибке
    """
    user_id = getattr(event.from_user, 'id', None) if hasattr(event, 'from_user') else None
    
    if clear_state:
        await safe_clear_state(state, user_id)
    
    try:
        if isinstance(event, Message):
            await event.answer(error_message)
        elif isinstance(event, CallbackQuery):
            await event.answer(error_message, show_alert=True)
    except Exception as e:
        logger.error(f"Failed to send error message to user {user_id}: {e}")

async def ensure_state_cleared_on_exit(
    state: FSMContext, 
    user_id: Optional[int] = None,
    success_message: Optional[str] = None,
    event: Optional[Message | CallbackQuery] = None
) -> None:
    """
    Гарантированная очистка состояния при выходе из FSM
    
    Args:
        state: FSM контекст
        user_id: ID пользователя для логирования
        success_message: Сообщение об успешном завершении (опционально)
        event: Событие для отправки сообщения (опционально)
    """
    await safe_clear_state(state, user_id)
    
    if success_message and event:
        try:
            if isinstance(event, Message):
                await event.answer(success_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(success_message)
        except Exception as e:
            logger.error(f"Failed to send success message to user {user_id}: {e}")

def log_fsm_transition(user_id: int, from_state: Optional[str], to_state: Optional[str], action: str = ""):
    """
    Логирование переходов между FSM состояниями
    
    Args:
        user_id: ID пользователя
        from_state: Предыдущее состояние
        to_state: Новое состояние
        action: Действие, вызвавшее переход
    """
    logger.info(f"FSM transition for user {user_id}: {from_state} -> {to_state} ({action})")

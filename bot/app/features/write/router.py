from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from app.fsm.write_states import WriteStates
from .action_write_button import on_write_button
from .state_input_text import on_text_input
from .auto_text_handler import on_auto_text_input
from .ttl_handlers import on_ttl_add, on_ttl_done, on_ttl_reset
from .action_send_now import cb_send_now
from .action_send_delayed import cb_send_delay, cb_cancel_delay
from .action_delete_draft import cb_delete_draft
from .action_blocking_continue import on_blocking_continue
import logging

router = Router()

# Отладочный middleware удален - проблема решена

# Кастомный фильтр для on_auto_text_input
async def auto_text_filter(message, state: FSMContext):
    """Фильтр для on_auto_text_input - исключает кнопки, FSM состояния WriteStates и пересланные сообщения"""
    # Проверяем, что это не кнопка
    if message.text and any(message.text.startswith(prefix) for prefix in ["✍️", "⚙️", "📊", "📌", "🔄", "🛡️"]):
        return False
    
    # ИСКЛЮЧАЕМ кнопку "Хорошо, не буду нарушать" - она должна обрабатываться специальным обработчиком
    if message.text == "✅ Хорошо, не буду нарушать":
        return False
    
    # Проверяем, что пользователь НЕ в любом из FSM состояний WriteStates
    current_state = await state.get_state()
    if current_state and "WriteStates" in str(current_state):
        return False
    
    # ИСКЛЮЧАЕМ пересланные сообщения - они должны обрабатываться другими роутерами
    if message.forward_from_chat or message.forward_from:
        return False
    
    return True

router.message.register(on_write_button, F.text == "✍️ Написать письмо")
router.message.register(on_text_input, StateFilter(WriteStates.INPUT_TEXT))
# Обработчик кнопки "Хорошо, не буду нарушать" - должен быть ПЕРЕД auto_text_input
router.message.register(on_blocking_continue, F.text == "✅ Хорошо, не буду нарушать")
# Автоматическая обработка текста для обычных пользователей (должен быть последним)
# НЕ обрабатываем кнопки - они должны обрабатываться специфичными обработчиками
# НЕ обрабатываем сообщения в FSM состояниях WriteStates - они обрабатываются соответствующими обработчиками
router.message.register(on_auto_text_input, auto_text_filter)

router.callback_query.register(on_ttl_add, F.data.startswith("ttl_add:"), StateFilter(WriteStates.CHOOSE_TTL))
router.callback_query.register(on_ttl_done, F.data == "ttl_done", StateFilter(WriteStates.CHOOSE_TTL))
router.callback_query.register(on_ttl_reset, F.data == "ttl_reset", StateFilter(WriteStates.CHOOSE_TTL))

router.callback_query.register(cb_send_now, F.data.startswith("send_now:"), StateFilter(WriteStates.PREVIEW))
router.callback_query.register(cb_send_delay, F.data.startswith("send_delay:"), StateFilter(WriteStates.PREVIEW))
router.callback_query.register(cb_cancel_delay, F.data.startswith("cancel_delay:"))
router.callback_query.register(cb_delete_draft, F.data.startswith("delete_draft:"))

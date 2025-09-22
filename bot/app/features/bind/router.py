from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from .start_payload import cmd_start_payload

router = Router()

# Кастомный фильтр для команд /start с параметрами
async def start_with_payload_filter(message: types.Message) -> bool:
    """Фильтр, который срабатывает только для команд /start с параметрами"""
    if not message.text:
        return False
    
    parts = message.text.split()
    if len(parts) < 2:
        return False  # Нет параметров - пропускаем
    
    return parts[0] == "/start"

router.message.register(cmd_start_payload, start_with_payload_filter)

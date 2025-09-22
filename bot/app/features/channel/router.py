from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from .cb_extend_unified import cb_extend_unified
from .cb_contact_author import cb_contact

async def cb_custom_button(c: types.CallbackQuery):
    """Обработчик для кастомных кнопок"""
    await c.answer("Кастомная кнопка нажата! 🎉")

router = Router()

# Унифицированный обработчик для всех extend операций
router.callback_query.register(cb_extend_unified, lambda c: c.data.startswith("ext:"))

# Обработчик для контакта с автором
router.callback_query.register(cb_contact, lambda c: c.data == "contact")

# Обработчик для кастомных кнопок
router.callback_query.register(cb_custom_button, lambda c: c.data.startswith("custom:"))

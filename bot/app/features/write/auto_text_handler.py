from aiogram import types
from aiogram.fsm.context import FSMContext
from app.fsm.write_states import WriteStates
from app.texts.prompts import PROMPT_INPUT
from app.infra.repo.users_repo import UsersRepo
from app.core.config import settings
import logging

async def on_auto_text_input(m: types.Message, state: FSMContext, db, active_mailbox_id: int, tz):
    """Автоматически переводит обычных пользователей в состояние INPUT_TEXT для обработки письма"""
    
    logging.info(f"AUTO TEXT HANDLER: Processing message from user {m.from_user.id}: '{m.text[:50] if m.text else 'No text'}...'")
    
    # Проверяем, что пользователь не админ
    users_repo = UsersRepo(db)
    role = await users_repo.get_role(m.from_user.id)
    is_admin = role in ("admin", "superadmin") or (settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID)
    
    if is_admin:
        # Админы используют обычный флоу с кнопками
        logging.info(f"AUTO TEXT HANDLER: User {m.from_user.id} is admin, skipping auto text processing")
        return False
    
    # Проверяем, что у пользователя есть активный ящик
    if not active_mailbox_id:
        await m.answer(
            "❌ У вас не настроен активный почтовый ящик.\n\n"
            "Для написания писем необходимо:\n"
            "1. Создать почтовый ящик в настройках\n"
            "2. Или привязаться к существующему ящику\n\n"
            "Обратитесь к администратору для настройки ящика."
        )
        return True
    
    # Проверяем, что это не команда
    if m.text and m.text.startswith('/'):
        return False
    
    # Проверяем, что это не кнопка
    button_texts = ["✍️ Написать письмо", "⚙️ Настройки", "📊 Статистика", "📌 Закрепить пост", "🔄 Обновить", "🛡️ Антиспам", "👤 Добавить админа", "🗑️ Удалить админа", "➕ Создать почтовый ящик", "📦 Управление ящиками", "🔙 Назад"]
    if m.text in button_texts:
        logging.info(f"AUTO TEXT HANDLER: Skipping button text: {m.text}")
        return False
    
    # Обрабатываем как письмо - просто переводим в состояние INPUT_TEXT
    text = (m.text or "").strip()
    if not text:
        await m.answer("Пустой текст. Напишите письмо текстом.")
        return True
    
    logging.info(f"AUTO TEXT INPUT by user {m.from_user.id}: {text[:50]}...")
    
    # Устанавливаем состояние и данные - остальная логика будет в on_text_input
    await state.clear()
    await state.set_state(WriteStates.INPUT_TEXT)
    await state.update_data(text=text)
    
    # Теперь вызываем обработчик INPUT_TEXT для полной обработки
    from .state_input_text import on_text_input
    await on_text_input(m, state, db, tz, active_mailbox_id)
    
    return True

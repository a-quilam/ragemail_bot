from aiogram import types
from aiogram.fsm.context import FSMContext
from app.fsm.write_states import WriteStates
from app.texts.prompts import PROMPT_INPUT
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.relays_repo import RelaysRepo
from app.core.config import settings
import logging
import time

async def on_auto_text_input(m: types.Message, state: FSMContext, db, active_mailbox_id: int, tz):
    """Автоматически переводит обычных пользователей в состояние INPUT_TEXT для обработки письма"""
    
    logging.info(f"AUTO TEXT HANDLER: Processing message from user {m.from_user.id}: '{m.text[:50] if m.text else 'No text'}...'")
    
    # Проверяем, что пользователь не админ
    users_repo = UsersRepo(db)
    role = await users_repo.get_role(m.from_user.id)
    is_admin = role in ("admin", "superadmin") or (settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID)
    
    if is_admin:
        # Админы используют обычный флоу с кнопками
        current_state = await state.get_state()
        
        # Если админ застрял в FSM состоянии (не в WriteStates), очищаем его
        # НО НЕ очищаем AntispamStates - это может нарушить работу антиспама
        if current_state and not str(current_state).startswith("WriteStates") and not str(current_state).startswith("AntispamStates"):
            logging.info(f"AUTO TEXT HANDLER: Clearing stuck FSM state for admin {m.from_user.id}: {current_state}")
            await state.clear()
            await m.answer("🔄 Состояние сброшено. Вы можете продолжить работу.")
        
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
    
    # ИСКЛЮЧАЕМ реплаи - они должны обрабатываться relay_router
    if m.reply_to_message:
        logging.info(f"AUTO TEXT HANDLER: Skipping reply message from user {m.from_user.id}")
        return False
    
    # Проверяем, что это не кнопка
    button_texts = ["✍️ Написать", "✍️ Написать письмо", "⚙️ Настройки", "📊 Статистика", "📌 Закрепить пост", "🔄 Обновить", "🛡️ Антиспам", "👤 Добавить админа", "🗑️ Удалить админа", "➕ Создать почтовый ящик", "📦 Управление ящиками", "🔙 Назад", "✅ Хорошо, не буду нарушать"]
    if m.text in button_texts:
        logging.info(f"AUTO TEXT HANDLER: Skipping button text: {m.text}")
        return False
    
    # ИСКЛЮЧАЕМ пересланные сообщения - они должны обрабатываться другими роутерами
    if m.forward_from_chat or m.forward_from:
        logging.info(f"AUTO TEXT HANDLER: Skipping forwarded message from user {m.from_user.id}")
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
    # Проверяем, что bot доступен
    if m.bot is None:
        logging.error(f"AUTO TEXT HANDLER: bot is None for user {m.from_user.id}")
        await m.answer("❌ Ошибка: объект бота не найден. Попробуйте еще раз.")
        return True
    
    await on_text_input(m, state, db, tz, active_mailbox_id, bot=m.bot)
    
    return True
